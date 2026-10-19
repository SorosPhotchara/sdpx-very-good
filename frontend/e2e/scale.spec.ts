import { expect, test } from '@playwright/test'

test('200 students: evaluation rendering, deferred reports and concurrent reads', async ({ page, request }) => {
  test.setTimeout(90000)
  const api = 'http://127.0.0.1:8000'
  const headers = { Authorization: 'Bearer mock:teacher@example.edu' }
  const name = `Scale 200 ${Date.now()}`
  const classroomResponse = await request.post(`${api}/classrooms/`, { headers, data: { name } })
  expect(classroomResponse.ok()).toBeTruthy()
  const classroom = await classroomResponse.json()
  const roster = 'email,groupname\n' + Array.from({ length: 200 }, (_, i) => `student${i + 1}@example.edu,Group ${Math.floor(i / 20)}`).join('\n')
  const imported = await request.post(`${api}/classrooms/${classroom.id}/roster/import`, { headers, data: { csv_text: roster } })
  expect((await imported.json()).imported).toBe(200)
  const deadline = new Date(Date.now() + 86400000).toISOString()
  const created = await request.post(`${api}/classrooms/${classroom.id}/assignments`, { headers, data: {
    title: name, group_score: 10, individual_score: 10, group_deadline: deadline, individual_deadline: deadline,
    group_criteria: [{ name: 'Quality', weight: 100 }], individual_criteria: [{ name: 'Contribution', weight: 100 }],
  } })
  expect(created.ok()).toBeTruthy()
  const assignment = await created.json()
  const published = await request.post(`${api}/assignments/${assignment.id}/publish`, { headers })
  expect(published.ok()).toBeTruthy()
  await page.goto('/')
  await page.getByRole('button', { name: 'EN', exact: true }).click()
  await page.getByRole('button', { name: /Explore as student/ }).click()
  await expect(page.getByRole('button', { name: new RegExp(name) })).toBeVisible()
  const reads: string[] = []
  page.on('request', req => { if (req.method() === 'GET') reads.push(req.url()) })
  const started = Date.now()
  await page.getByRole('button', { name: new RegExp(name) }).click()
  const group = page.getByRole('heading', { name: 'Group evaluation', exact: true }).locator('..')
  await expect(group.locator('input[type=radio]').first()).toBeVisible()
  const renderMs = Date.now() - started
  expect(renderMs).toBeLessThan(2000)
  expect(reads.some(url => /\/report$|\/scores\/me$|\/evaluation\/individual$/.test(url))).toBe(false)
  await page.locator('summary').filter({ hasText: 'Individual evaluation' }).click()
  await expect(page.getByRole('heading', { name: 'Individual evaluation', exact: true }).locator('..').locator('input[type=radio]').first()).toBeVisible()
  const latencies = await Promise.all(Array.from({ length: 20 }, async (_, i) => {
    const start = Date.now()
    const response = await request.get(`${api}/assignments/${assignment.id}/evaluation/individual`, { headers: { Authorization: `Bearer mock:student${i + 1}@example.edu` } })
    expect(response.ok()).toBeTruthy()
    expect((await response.json()).pairs.length).toBeGreaterThan(0)
    return Date.now() - start
  }))
  expect(Math.max(...latencies)).toBeLessThan(2000)
  console.log(`200 students, 10 groups: browser=${renderMs}ms; 20 concurrent reads max=${Math.max(...latencies)}ms`)
})
