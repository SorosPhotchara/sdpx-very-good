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

  await page.locator('summary').filter({ hasText: 'Create assignment' }).click()
  await page.getByLabel('Title').fill('New review')
  const groupSection = page.getByRole('group', { name: 'Group evaluation' })
  await groupSection.getByLabel('Deadline').fill(new Date(Date.now() + 2 * 86400_000).toISOString().slice(0, 16))
  await groupSection.getByLabel('Weight %').fill('90')
  await page.getByRole('button', { name: 'Create assignment' }).click()
  await expect(page.getByText('Group evaluation weights total 90%; they must total 100%.')).toBeVisible()

  await groupSection.getByLabel('Weight %').fill('100')
  await page.getByRole('button', { name: 'Create assignment' }).click()
  await expect(page.getByText('Assignment created.')).toBeVisible()
})

test('classroom tools fit inside the sidebar at narrow widths', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'EN', exact: true }).click()
  await page.getByRole('button', { name: /Explore as instructor/ }).click()
  await page.getByRole('button', { name: /Manage classroom/ }).click()

  await page.getByText('Move student between groups').click()
  await expect(page.getByLabel('Choose student')).toBeVisible()

  for (const width of [390, 720, 800, 1000, 1280]) {
    await page.setViewportSize({ width, height: 900 })
    const overflowing = await page.getByTestId('workspace-side').evaluate((sidebar) => {
      const bounds = sidebar.getBoundingClientRect()
      return [...sidebar.querySelectorAll('input, select, button, .instructor-list, details')]
        .filter((element) => {
          const rect = element.getBoundingClientRect()
          return rect.left < bounds.left - 1 || rect.right > bounds.right + 1
        })
        .map((element) => element.tagName.toLowerCase())
    })
    expect(overflowing, `sidebar controls overflow at ${width}px`).toEqual([])
    expect(await page.evaluate(() => document.documentElement.scrollWidth), `page widens at ${width}px`).toBeLessThanOrEqual(width)
  }
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
  for (const width of [390, 720]) {
    await page.setViewportSize({ width, height: 900 })
    await expect(groupEvaluation.getByTestId('pair-candidates').first()).toBeVisible()
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width)
  }
  await groupEvaluation.locator('input[type=radio]:not(:checked)').first().click()
  await expect(groupEvaluation.getByText('Draft saved.')).toBeVisible()
  await groupEvaluation.getByRole('button', { name: 'Submit saved answers' }).click()
  await groupEvaluation.getByRole('button', { name: 'Confirm submission' }).click()
  await expect(groupEvaluation.getByText(/Submitted 1 of \d+ pairs\./)).toBeVisible()
  await page.getByRole('button', { name: 'Sign out' }).click()
  await page.reload()
  await expect(page.getByRole('button', { name: /Explore as student/ })).toBeVisible()
})

test('student choice responds before the draft request finishes without moving its label', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'EN', exact: true }).click()
  await page.getByRole('button', { name: /Explore as student/ }).click()
  const choice = page.locator('.evaluation-pair').first().locator('input[type=radio]').first()
  await expect(choice).toBeVisible()
  const label = choice.locator('..')
  const before = await label.evaluate((element) => ({
    width: element.getBoundingClientRect().width,
    weight: getComputedStyle(element).fontWeight,
  }))
  let releaseRequest!: () => void
  const pendingRequest = new Promise<void>((resolve) => { releaseRequest = resolve })
  await page.route('**/evaluation/group/draft', async (route) => {
    await pendingRequest
    await route.continue()
  })

  try {
    await choice.click()
    expect(await choice.isChecked()).toBe(true)
    const after = await label.evaluate((element) => ({
      width: element.getBoundingClientRect().width,
      weight: getComputedStyle(element).fontWeight,
    }))
    expect(after).toEqual(before)
  } finally {
    releaseRequest()
  }
})
