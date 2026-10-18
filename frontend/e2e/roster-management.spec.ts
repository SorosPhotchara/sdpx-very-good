import { expect, test } from '@playwright/test'

const AUTH = { Authorization: 'Bearer mock:teacher@example.edu' }

test('instructor removes one student from a classroom that has no evaluation', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'EN', exact: true }).click()
  await page.getByRole('button', { name: /Explore as instructor/ }).click()
  const name = `Roster classroom ${Date.now()}`
  await page.getByLabel('Add classroom').fill(name)
  await page.getByLabel('Add classroom').press('Enter')
  await expect(page.getByRole('heading', { name, exact: true })).toBeVisible()
  const rooms = await page.request.get('http://127.0.0.1:8000/classrooms/', { headers: AUTH })
  const id = (await rooms.json()).find((room: { name: string }) => room.name === name).id

  await page.getByRole('button', { name: /Manage classroom/ }).click()
  await page.getByLabel('Import student roster (CSV)').setInputFiles({
    name: 'roster.csv',
    mimeType: 'text/csv',
    buffer: Buffer.from('email,groupname\nfirst@example.edu,Alpha\nsecond@example.edu,Alpha\nthird@example.edu,Beta'),
  })
  await expect(page.getByText('Imported 3 students.', { exact: true })).toBeVisible()
  await page.getByTestId('refresh-roster').click()
  await expect(page.getByTestId('roster-table').locator('tbody tr')).toHaveCount(3)

  const roster = await (await page.request.get(`http://127.0.0.1:8000/students/?classroom_id=${id}`, { headers: AUTH })).json()
  const victim = roster.find((student: { email: string }) => student.email === 'second@example.edu')
  let deletes = 0
  page.on('request', request => {
    if (request.method() === 'DELETE' && request.url().endsWith(`/classrooms/${id}/students/${victim.id}`)) deletes++
  })

  await page.getByTestId(`remove-student-${victim.id}`).click()
  const dialog = page.getByTestId('remove-student-dialog')
  await expect(dialog).toBeVisible()
  await expect(page.getByTestId('confirm-remove-student')).toBeDisabled()
  await page.getByTestId('confirm-student-email').fill('wrong@example.edu')
  await expect(page.getByTestId('confirm-remove-student')).toBeDisabled()
  await dialog.getByRole('button', { name: 'Cancel', exact: true }).click()
  expect(deletes).toBe(0)
  await expect(page.getByTestId(`roster-row-${victim.id}`)).toBeVisible()

  await page.getByTestId(`remove-student-${victim.id}`).click()
  await page.getByTestId('confirm-student-email').fill('second@example.edu')
  await page.getByTestId('confirm-remove-student').click()
  await expect(dialog).toHaveCount(0)
  await expect(page.getByText('Student removed from the classroom.', { exact: true })).toBeVisible()
  await expect(page.getByTestId(`roster-row-${victim.id}`)).toHaveCount(0)
  await expect(page.getByTestId('roster-table').locator('tbody tr')).toHaveCount(2)
  expect(deletes).toBe(1)

  const remaining = await (await page.request.get(`http://127.0.0.1:8000/students/?classroom_id=${id}`, { headers: AUTH })).json()
  expect(remaining.map((student: { email: string }) => student.email).sort()).toEqual(['first@example.edu', 'third@example.edu'])
})

test('removal is refused once an evaluation exists and a failure keeps the dialog open', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'EN', exact: true }).click()
  await page.getByRole('button', { name: /Explore as instructor/ }).click()
  await page.getByRole('navigation', { name: 'Classrooms' }).getByRole('button', { name: /PairEval Demo/ }).click()
  await page.getByRole('button', { name: /Manage classroom/ }).click()

  const rows = page.getByTestId('roster-table').locator('tbody tr')
  await expect(rows.first()).toBeVisible()
  const published = await (await page.request.get('http://127.0.0.1:8000/classrooms/', { headers: AUTH })).json()
  const demo = published.find((room: { name: string }) => room.name === 'PairEval Demo')
  const roster = await (await page.request.get(`http://127.0.0.1:8000/students/?classroom_id=${demo.id}`, { headers: AUTH })).json()
  const before = roster.length
  const target = roster[0]

  // The demo classroom is published, so the API refuses and nothing is mutated.
  await page.getByTestId(`remove-student-${target.id}`).click()
  await page.getByTestId('confirm-student-email').fill(target.email)
  await page.getByTestId('confirm-remove-student').click()
  await expect(page.getByRole('alert').filter({ hasText: 'Cannot remove a student after an evaluation exists' })).toBeVisible()
  await expect(page.getByTestId('remove-student-dialog')).toBeVisible()
  await expect(page.getByTestId('confirm-remove-student')).toBeEnabled()
  await page.getByTestId('remove-student-dialog').getByRole('button', { name: 'Cancel', exact: true }).click()

  await page.route('**/classrooms/*/students/*', route => route.fulfill({
    status: 503, contentType: 'application/json', body: JSON.stringify({ detail: 'Try again later.' }),
  }))
  await page.getByTestId(`remove-student-${target.id}`).click()
  await page.getByTestId('confirm-student-email').fill(target.email)
  await page.getByTestId('confirm-remove-student').click()
  await expect(page.getByRole('alert').filter({ hasText: 'Try again later.' })).toBeVisible()
  await expect(page.getByTestId('remove-student-dialog')).toBeVisible()
  await expect(page.getByTestId('confirm-remove-student')).toBeEnabled()
  await page.unroute('**/classrooms/*/students/*')

  const after = await (await page.request.get(`http://127.0.0.1:8000/students/?classroom_id=${demo.id}`, { headers: AUTH })).json()
  expect(after.length).toBe(before)
})
