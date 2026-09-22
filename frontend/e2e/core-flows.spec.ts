import { expect, test } from '@playwright/test'

test('switches between Thai and English on the sign-in page', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByText('เข้าสู่พื้นที่การเรียนรู้')).toBeVisible()

  await page.getByRole('button', { name: 'EN', exact: true }).click()
  await expect(page.getByText('Enter your workspace')).toBeVisible()
  await expect(page.getByRole('button', { name: /Explore as instructor/ })).toBeVisible()
})

test('instructor creates a classroom and imports its roster', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'EN', exact: true }).click()
  await page.getByRole('button', { name: /Explore as instructor/ }).click()
  await expect(page.getByText('teacher@example.edu')).toBeVisible()

  const classroomName = `E2E Classroom ${Date.now()}`
  const classroomInput = page.getByLabel('Add classroom')
  await classroomInput.fill(classroomName)
  await classroomInput.press('Enter')
  await expect(page.getByRole('heading', { name: classroomName })).toBeVisible()

  await page.getByRole('button', { name: /Manage classroom/ }).click()
  await page.getByLabel('Import student roster (CSV)').setInputFiles({
    name: 'roster.csv',
    mimeType: 'text/csv',
    buffer: Buffer.from([
      'email,groupname',
      'one@example.edu,Alpha',
      'two@example.edu,Alpha',
      'three@example.edu,Beta',
      'four@example.edu,Beta',
      'five@example.edu,Gamma',
      'six@example.edu,Gamma',
    ].join('\n')),
  })
  await expect(page.getByText('Imported 6 students.')).toBeVisible()
  await page.getByLabel('Student Google email').fill('seven@example.edu')
  await page.getByLabel('Group name').fill('Gamma')
  await page.getByRole('button', { name: 'Add student', exact: true }).click()
  await expect(page.getByText('Added seven@example.edu to Gamma.')).toBeVisible()
})

test('student saves and submits a pairwise evaluation', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'EN', exact: true }).click()
  await page.getByRole('button', { name: /Explore as student/ }).click()
  await expect(page.getByText('student1@example.edu')).toBeVisible()
  await expect(page.getByText('Team project review')).toBeVisible()
  await page.reload()
  await expect(page.getByText('Team project review')).toBeVisible()

  const groupEvaluation = page.getByRole('heading', { name: 'Group evaluation' }).locator('..')
  await groupEvaluation.locator('input[type=radio]:not(:checked)').first().click()
  await expect(groupEvaluation.getByText('Draft saved.')).toBeVisible()
  await groupEvaluation.getByRole('button', { name: 'Submit saved answers' }).click()
  await groupEvaluation.getByRole('button', { name: 'Confirm submission' }).click()
  await expect(groupEvaluation.getByText(/Submitted 1 of \d+ pairs\./)).toBeVisible()
  await page.getByRole('button', { name: 'Sign out' }).click()
  await page.reload()
  await expect(page.getByRole('button', { name: /Explore as student/ })).toBeVisible()
})
