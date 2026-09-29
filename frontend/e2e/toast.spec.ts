import { expect, test } from '@playwright/test'

test('action notices are readable mobile toasts, repeatable and dismissible', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 640 })
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.goto('/')
  await page.getByRole('button', { name: 'EN', exact: true }).click()
  await page.getByRole('button', { name: /Explore as instructor/ }).click()
  await page.getByRole('button', { name: /Manage classroom/ }).click()
  const input = page.getByLabel('Classroom name', { exact: true })
  const original = await input.inputValue()
  const toast = page.getByTestId('action-toast')
  for (const name of [original + ' toast', original]) {
    await input.fill(name)
    await page.getByRole('button', { name: 'Save classroom name' }).click()
    await expect(toast.getByRole('status')).toHaveText('Classroom renamed.')
    expect(await toast.evaluate(element => getComputedStyle(element).position)).toBe('fixed')
    expect(await toast.evaluate(element => getComputedStyle(element).animationName)).toBe('none')
    const bounds = await toast.boundingBox()
    expect(bounds!.x).toBeGreaterThanOrEqual(0)
    expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(320)
    expect(bounds!.y + bounds!.height).toBeCloseTo(624, 0)
    await toast.getByRole('button', { name: 'Dismiss notification' }).focus()
    await page.keyboard.press('Escape')
    await expect(toast).toBeHidden()
  }
  await input.fill(original + ' auto-dismiss')
  await page.getByRole('button', { name: 'Save classroom name' }).click()
  await expect(toast).toBeVisible()
  await expect(toast).toBeHidden({ timeout: 10000 })
  await input.fill(original)
  await page.getByRole('button', { name: 'Save classroom name' }).click()
  await expect(toast).toBeVisible()
  await toast.getByRole('button', { name: 'Dismiss notification' }).click()
  await expect(toast).toBeHidden()
})

test('toast close control stays centered inside the card at desktop and mobile sizes', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.addInitScript(() => sessionStorage.clear())
  await page.route('**/health', route => route.fulfill({ json: { status: 'ok' } }))
  await page.route('**/me', route => route.fulfill({ status: 500, json: { detail: 'Sign-in failed' } }))
  await page.route('**/classrooms/', route => route.fulfill({ json: [] }))

  for (const width of [320, 1440]) {
    await page.setViewportSize({ width, height: 720 })
    await page.goto('/')
    await page.getByRole('button', { name: 'EN', exact: true }).click()
    await page.getByRole('button', { name: /Explore as instructor/ }).click()

    const toast = page.getByTestId('action-toast')
    const close = toast.getByRole('button', { name: 'Dismiss notification' })
    await expect(toast).toBeVisible()
    const bounds = (await toast.boundingBox())!
    const closeBounds = (await close.boundingBox())!
    const iconBounds = (await close.locator('svg').boundingBox())!
    expect(closeBounds.x).toBeGreaterThanOrEqual(bounds.x + 8)
    expect(closeBounds.x + closeBounds.width).toBeLessThanOrEqual(bounds.x + bounds.width - 8)
    expect(closeBounds.y).toBeGreaterThanOrEqual(bounds.y + 8)
    expect(closeBounds.y + closeBounds.height).toBeLessThanOrEqual(bounds.y + bounds.height - 8)
    expect(closeBounds.width).toBeGreaterThanOrEqual(44)
    expect(closeBounds.height).toBeGreaterThanOrEqual(44)
    expect(Math.abs(iconBounds.x + iconBounds.width / 2 - closeBounds.x - closeBounds.width / 2)).toBeLessThanOrEqual(1)
    expect(Math.abs(iconBounds.y + iconBounds.height / 2 - closeBounds.y - closeBounds.height / 2)).toBeLessThanOrEqual(1)
    expect(await close.evaluate(element => getComputedStyle(element).transitionDuration)).toBe('0s')
    await close.focus()
    await expect(close).toBeFocused()
    await page.keyboard.press('Escape')
    await expect(toast).toBeHidden()
  }
})
