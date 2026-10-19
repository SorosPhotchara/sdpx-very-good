import { expect, test } from '@playwright/test'

test('instructor assigns pairs in bulk by evaluation mode and group', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'EN', exact: true }).click()
  await page.getByRole('button', { name: /Explore as instructor/ }).click()
  await page.getByRole('navigation', { name: 'Classrooms' }).getByRole('button', { name: /PairEval Demo/ }).click()
  await page.locator('summary').filter({ hasText: 'Instructor pairwise evaluation' }).click()

  const planner = page.getByTestId('instructor-pair-planner')
  await expect(planner.getByText('3 pairs · 0 assigned to me')).toBeVisible()
  await planner.getByRole('button', { name: 'Select all unassigned' }).click()
  await expect(planner.getByTestId('assign-instructor-pair')).toHaveText('Assign 3 to me')
  await planner.getByTestId('assign-instructor-pair').click()
  await expect(planner.getByText('3 pairs · 3 assigned to me')).toBeVisible()
  await expect(page.getByTestId('instructor-assigned-pairs').locator('.evaluation-pair')).toHaveCount(3)

  await planner.getByRole('button', { name: /Individual evaluation/ }).click()
  await planner.getByLabel('Filter by group').selectOption({ label: 'Aurora' })
  await expect(planner.getByText('3 pairs · 0 assigned to me')).toBeVisible()
  await planner.getByRole('button', { name: 'Select all unassigned' }).click()
  await planner.getByTestId('assign-instructor-pair').click()
  await expect(planner.getByText('3 pairs · 3 assigned to me')).toBeVisible()
  await expect(page.getByTestId('instructor-assigned-pairs').locator('.evaluation-pair')).toHaveCount(3)

  await planner.getByLabel('Filter by group').selectOption({ label: 'Beacon' })
  await expect(planner.getByText('3 pairs · 0 assigned to me')).toBeVisible()
  await planner.getByRole('button', { name: 'Select all unassigned' }).click()
  await planner.getByTestId('assign-instructor-pair').click()
  await planner.getByLabel('Filter by group').selectOption({ label: 'Aurora' })
  await expect(page.getByTestId('instructor-assigned-pairs').locator('.evaluation-pair')).toHaveCount(3)
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390)
})
