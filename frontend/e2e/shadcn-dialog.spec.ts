import { expect, test } from '@playwright/test'

test('group move confirmation traps focus, cancels safely and restores its trigger', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'EN', exact: true }).click()
  await page.getByRole('button', { name: /Explore as instructor/ }).click()
  await page.getByRole('button', { name: /Manage classroom/ }).click()
  await page.getByText('Move student between groups', { exact: true }).click()
  const students = page.getByLabel('Choose student')
  await expect.poll(() => students.locator('option').count()).toBeGreaterThan(1)
  await students.selectOption({ index: 1 })
  await page.getByLabel('Target group').selectOption({ index: 2 })
  let writes = 0
  page.on('request', request => {
    if (/\/students\/\d+\/group$/.test(request.url()) && request.method() !== 'OPTIONS') writes++
  })
  const trigger = page.getByRole('button', { name: 'Move', exact: true })
  await trigger.click()
  const dialog = page.getByRole('alertdialog', { name: 'Move student between groups' })
  await expect(dialog).toBeVisible()
  await expect(dialog.getByRole('button', { name: 'Cancel', exact: true })).toBeFocused()
  for (let i = 0; i < 3; i++) {
    await page.keyboard.press('Tab')
    expect(await dialog.evaluate(element => element.contains(document.activeElement))).toBe(true)
  }
  await page.keyboard.press('Escape')
  await expect(dialog).toHaveCount(0)
  await expect(trigger).toBeFocused()
  expect(writes).toBe(0)
  await trigger.click()
  await dialog.getByRole('button', { name: 'Cancel', exact: true }).click()
  await expect(dialog).toHaveCount(0)
  await expect(trigger).toBeFocused()
  expect(writes).toBe(0)
})
