import { expect, test } from '@playwright/test'

test('Sonner renders status icons with mobile gutters and supports swipe dismissal', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.goto('/')
  await page.getByRole('button', { name: 'EN', exact: true }).click()
  await page.getByRole('button', { name: /Explore as student/ }).click()
  await page.locator('.evaluation-pair').first().locator('input:not(:checked)').first().click()
  const notice = page.getByTestId('action-toast')
  await expect(notice).toHaveAttribute('data-sonner-toast', '')
  await expect(notice).toHaveAttribute('data-type', 'success')
  await expect(notice.locator('[data-icon] svg')).toBeVisible()
  const bounds = (await notice.boundingBox())!
  const clientWidth = await page.evaluate(() => document.documentElement.clientWidth)
  expect(bounds.x).toBeGreaterThanOrEqual(16)
  expect(bounds.x + bounds.width).toBeLessThanOrEqual(clientWidth - 16)
  await page.mouse.move(bounds.x + 70, bounds.y + bounds.height / 2)
  await page.mouse.down()
  await page.mouse.move(bounds.x + 290, bounds.y + bounds.height / 2, { steps: 10 })
  await page.mouse.up()
  await expect(notice).toBeHidden()
})
