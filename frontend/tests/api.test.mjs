import assert from "node:assert/strict"
import { after, before, test } from "node:test"
import { createServer } from "vite"

const server = await createServer({ server: { middlewareMode: true } })
const api = await server.ssrLoadModule("/src/api.ts")
const originalFetch = globalThis.fetch

before(() => {
  api.setCredential("test-id-token")
  globalThis.fetch = async (url, options) => {
    assert.equal(url, "http://localhost:8000/classrooms/")
    assert.equal(options.method, "POST")
    assert.equal(options.headers.Authorization, "Bearer test-id-token")
    assert.deepEqual(JSON.parse(options.body), {
      name: "Algorithms",
      instructor_emails: "",
    })
    return new Response(JSON.stringify({ id: 1, name: "Algorithms" }), {
      status: 201,
      headers: { "Content-Type": "application/json" },
    })
  }
})

after(async () => {
  api.setCredential("")
  globalThis.fetch = originalFetch
  await server.close()
})

test("classroom creation sends the expected request and returns the created classroom", async () => {
  assert.deepEqual(await api.createClassroom("Algorithms"), {
    id: 1,
    name: "Algorithms",
  })
})

test("an API failure rejects instead of appearing to create a classroom", async () => {
  globalThis.fetch = async () => new Response("failure", { status: 500 })
  await assert.rejects(api.createClassroom("Algorithms"), /API request failed: 500/)
})

test("classroom requests require a Google credential", async () => {
  api.setCredential("")
  await assert.rejects(api.getClassrooms(), /Sign in required/)
})

test("roster import sends CSV text only for the selected classroom", async () => {
  api.setCredential("test-id-token")
  globalThis.fetch = async (url, options) => {
    assert.equal(url, "http://localhost:8000/classrooms/7/roster/import")
    assert.equal(options.headers.Authorization, "Bearer test-id-token")
    assert.deepEqual(JSON.parse(options.body), { csv_text: "email,groupname\na@example.edu,A" })
    return new Response(JSON.stringify({ imported: 1, errors: [] }), { status: 200 })
  }
  assert.deepEqual(await api.importRoster(7, "email,groupname\na@example.edu,A"), {
    imported: 1,
    errors: [],
  })
})

test("adding one student sends their email and group to the selected classroom", async () => {
  api.setCredential("test-id-token")
  globalThis.fetch = async (url, options) => {
    assert.equal(url, "http://localhost:8000/students/")
    assert.equal(options.method, "POST")
    assert.equal(options.headers.Authorization, "Bearer test-id-token")
    assert.deepEqual(JSON.parse(options.body), {
      classroom_id: 7, email: "student@example.edu", group_name: "Team A",
    })
    return new Response(JSON.stringify({
      id: 3, classroom_id: 7, email: "student@example.edu", group_name: "Team A", group_id: 2,
    }), { status: 200 })
  }
  const student = await api.addStudent(7, "student@example.edu", "Team A")
  assert.equal(student.group_id, 2)
})

test("draft save sends only changed choices and submit sends the saved page snapshot request", async () => {
  api.setCredential("test-id-token")
  let requests = 0
  globalThis.fetch = async (url, options) => {
    requests++
    assert.equal(options.headers.Authorization, "Bearer test-id-token")
    if (requests === 1) {
      assert.equal(url, "http://localhost:8000/assignments/9/evaluation/group/draft")
      assert.equal(options.method, "PUT")
      assert.deepEqual(JSON.parse(options.body), { changes: [{ pair_id: 42, choice: 3 }] })
      return new Response(JSON.stringify({ assignment_id: 9, section: "group", pairs: [] }), { status: 200 })
    }
    assert.equal(url, "http://localhost:8000/assignments/9/evaluation/group/submit")
    assert.equal(options.method, "POST")
    assert.equal(options.body, undefined)
    return new Response(JSON.stringify({ submission_id: 3, answered: 1, assigned: 5 }), { status: 200 })
  }
  await api.saveEvaluationDraft(9, "group", [{ pair_id: 42, choice: 3 }])
  assert.deepEqual(await api.submitEvaluation(9, "group"), { submission_id: 3, answered: 1, assigned: 5 })
})
