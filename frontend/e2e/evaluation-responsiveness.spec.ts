import { expect, test, type APIRequestContext, type Page } from '@playwright/test'

async function openEvaluation(page: Page, request: APIRequestContext) {
  const api = 'http://127.0.0.1:8000'
  const headers = { Authorization: 'Bearer mock:teacher@example.edu' }
  const name = `Autosave fixture ${Date.now()}`
  const created = await request.post(`${api}/classrooms/`, { headers, data: { name } })
  expect(created.ok()).toBeTruthy()
  const classroom = await created.json()
  const roster = 'email,groupname\n' + Array.from({ length: 9 }, (_, i) => `student${i + 1}@example.edu,Group ${Math.floor(i / 3)}`).join('\n')
  expect((await request.post(`${api}/classrooms/${classroom.id}/roster/import`, { headers, data: { csv_text: roster } })).ok()).toBeTruthy()
  const assignmentResponse = await request.post(`${api}/classrooms/${classroom.id}/assignments`, { headers, data: {
    title: 'Autosave review', group_score: 10, group_deadline: new Date(Date.now() + 86400000).toISOString(),
    group_criteria: [{ name: 'Quality', weight: 50 }, { name: 'Teamwork', weight: 50 }],
  } })
  expect(assignmentResponse.ok()).toBeTruthy()
  const assignment = await assignmentResponse.json()
  expect((await request.post(`${api}/assignments/${assignment.id}/publish`, { headers })).ok()).toBeTruthy()
  await page.goto('/')
  await page.getByRole('button', { name: 'EN', exact: true }).click()
  await page.getByRole('button', { name: /Explore as student/ }).click()
  await page.getByRole('button', { name: new RegExp(name) }).click()
  await expect(page.locator('.evaluation-pair').nth(1)).toBeVisible()
  return name
}

test('students keep choosing while autosave is pending and the latest answers persist', async ({ page, request }) => {
  const roomName = await openEvaluation(page, request)
  const pairs = page.locator('.evaluation-pair')
  await expect(pairs.first()).toBeVisible()
  let release!: () => void
  const pending = new Promise<void>(resolve => { release = resolve })
  let requests = 0
  await page.route('**/evaluation/group/draft', async route => {
    if (++requests === 1) await pending
    await route.continue()
  })
  try {
    await pairs.first().locator('input').nth(1).click()
    await expect.poll(() => requests).toBe(1)
    const latest = pairs.first().locator('input').nth(4)
    await expect(latest).toBeEnabled({ timeout: 1000 })
    await latest.click()
    await pairs.nth(1).locator('input').nth(2).click()
    await expect(latest).toBeChecked()
    await expect(pairs.nth(1).locator('input').nth(2)).toBeChecked()
    await expect(page.getByRole('button', { name: 'Submit saved answers' })).toBeDisabled()
  } finally { release() }
  await expect(page.getByText('Draft saved.')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Submit saved answers' })).toBeEnabled()
  expect(requests).toBe(2)
  await page.reload()
  await page.getByRole('button', { name: new RegExp(roomName) }).click()
  await expect(pairs.first().locator('input').nth(4)).toBeChecked()
  await expect(pairs.nth(1).locator('input').nth(2)).toBeChecked()
})

test('failed autosave keeps the latest choices and blocks submission until retry succeeds', async ({ page, request }) => {
  const roomName = await openEvaluation(page, request)
  const pairs = page.locator('.evaluation-pair')
  await expect(pairs.first()).toBeVisible()
  let release!: () => void
  const pending = new Promise<void>(resolve => { release = resolve })
  let requests = 0
  await page.route('**/evaluation/group/draft', async route => {
    if (++requests === 1) {
      await pending
      await route.fulfill({ status: 503, json: { detail: 'Save temporarily unavailable.' } })
    } else await route.continue()
  })
  try {
    await pairs.first().locator('input').nth(0).click()
    await expect.poll(() => requests).toBe(1)
    await pairs.first().locator('input').nth(3).click()
    await pairs.nth(1).locator('input').nth(1).click()
  } finally { release() }
  await expect(page.getByTestId('action-toast')).toContainText('Save temporarily unavailable.')
  await expect(pairs.first().locator('input').nth(3)).toBeChecked()
  await expect(pairs.nth(1).locator('input').nth(1)).toBeChecked()
  await expect(page.getByRole('button', { name: 'Submit saved answers' })).toBeDisabled()
  await page.getByRole('button', { name: 'Retry', exact: true }).click()
  await expect(page.getByTestId('action-toast')).toContainText('Draft saved.')
  await expect(page.getByRole('button', { name: 'Submit saved answers' })).toBeEnabled()
  expect(requests).toBe(2)
  await page.reload()
  await page.getByRole('button', { name: new RegExp(roomName) }).click()
  await expect(pairs.first().locator('input').nth(3)).toBeChecked()
  await expect(pairs.nth(1).locator('input').nth(1)).toBeChecked()
})
