import { expect, test } from '@playwright/test'

const api = 'http://127.0.0.1:8000'
const instructor = { Authorization: 'Bearer mock:teacher@example.edu' }

// Covers the student-facing deadline, progress and interim-score signals the PRD requires:
// FR-EVAL-13 countdown, FR-SCORE-17 per-criterion submitted progress,
// FR-EVAL-06 unevaluated-pair warning and FR-SCORE-13 interim labelling.
test('countdown, per-criterion submitted progress, unevaluated warning and interim scores', async ({ page, request }) => {
  test.setTimeout(90000)
  const name = `Deadline signals ${Date.now()}`
  const classroom = await request.post(`${api}/classrooms/`, { headers: instructor, data: { name } })
  expect(classroom.ok()).toBeTruthy()
  const classroomId = (await classroom.json()).id
  const roster = 'email,groupname\n' + Array.from({ length: 9 },
    (_, i) => `student${i + 1}@example.edu,Group ${Math.floor(i / 3)}`).join('\n')
  const imported = await request.post(`${api}/classrooms/${classroomId}/roster/import`, { headers: instructor, data: { csv_text: roster } })
  expect((await imported.json()).imported).toBe(9)
  // Three days out so the countdown renders its days/hours/minutes form.
  const deadline = new Date(Date.now() + 3 * 86400000).toISOString()
  const created = await request.post(`${api}/classrooms/${classroomId}/assignments`, { headers: instructor, data: {
    title: name, group_score: 10, individual_score: 10, group_deadline: deadline, individual_deadline: deadline,
    // Two group criteria give each evaluator more than one pair, so one stays
    // unevaluated after the first answer and the warning has something to report.
    group_criteria: [{ name: 'Quality', weight: 60 }, { name: 'Clarity', weight: 40 }],
    individual_criteria: [{ name: 'Contribution', weight: 100 }],
  } })
  expect(created.ok()).toBeTruthy()
  const assignmentId = (await created.json()).id
  expect((await request.post(`${api}/assignments/${assignmentId}/publish`, { headers: instructor })).ok()).toBeTruthy()

  await page.goto('/')
  await page.getByRole('button', { name: 'EN', exact: true }).click()
  await page.getByRole('button', { name: /Explore as student/ }).click()
  await page.getByRole('button', { name: new RegExp(name) }).click()
  const evaluation = page.getByRole('heading', { name: 'Group evaluation', exact: true }).locator('..')

  // FR-EVAL-13: a live countdown, not just the deadline date.
  const countdown = evaluation.getByTestId('evaluation-countdown')
  await expect(countdown).toBeVisible()
  await expect(countdown).toHaveText(/\d+d \d+h \d+m left/)
  await expect(evaluation.getByText('Deadline:', { exact: false })).toBeVisible()

  // FR-SCORE-17: progress counts submitted pairs per criterion, so it starts at zero
  // even though a draft is saved below.
  const progress = evaluation.getByTestId('criterion-progress')
  await expect(progress.getByRole('progressbar')).toHaveCount(2)
  await expect(progress).toContainText('Quality')
  await expect(progress).toContainText('Clarity')
  await expect(progress).toContainText(/0 \/ \d+ pairs submitted/)
  await expect(progress.locator('progress[aria-label^="Quality"]')).toHaveAttribute('aria-label', /Quality: 0 of \d+ pairs submitted/)

  // FR-EVAL-06: the page warns while pairs remain unevaluated.
  await expect(evaluation.getByTestId('unanswered-notice')).toContainText(/pairs? still unevaluated/)
  await evaluation.locator('input[type=radio]').first().click()
  await expect(evaluation.getByText('Draft saved.', { exact: true })).toBeVisible()
  await expect(progress).toContainText(/0 \/ \d+ pairs submitted/)

  // The confirmation names how many pairs are still unevaluated before submitting.
  await evaluation.getByRole('button', { name: 'Submit saved answers', exact: true }).click()
  await expect(evaluation.getByTestId('unanswered-warning')).toContainText(/Warning: \d+ of \d+ pairs are still unevaluated/)
  await evaluation.getByRole('button', { name: 'Confirm submission', exact: true }).click()
  await expect(evaluation.getByText(/Submitted 1 of/)).toBeVisible()
  await expect(progress).toContainText(/1 \/ \d+ pairs submitted/)

  // FR-SCORE-13 / FR-REPORT-07: the student sees the interim label, not only the instructor.
  await page.locator('summary').filter({ hasText: 'Scores and coverage' }).click()
  const finality = page.getByTestId('score-finality')
  await expect(finality).toBeVisible()
  await expect(finality).toContainText('Group: Interim — may change')
  await expect(finality).toContainText('Individual: Interim — may change')
  const mine = await request.get(`${api}/assignments/${assignmentId}/my-scores`, { headers: { Authorization: 'Bearer mock:student1@example.edu' } })
  expect(await mine.json()).toMatchObject({ group_final: false, individual_final: false })
})
