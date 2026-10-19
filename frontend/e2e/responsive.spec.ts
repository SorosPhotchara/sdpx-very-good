import { expect, test, type Page } from '@playwright/test'

const widths = [320, 390, 768, 1024, 1440]

async function expectPageFits(page: Page, width: number) {
  await page.evaluate(() => document.fonts.ready)
  expect(await page.evaluate(() => document.documentElement.scrollWidth), `page overflow at ${width}px`).toBeLessThanOrEqual(width)
  const overflow = await page.locator('main').evaluate((main) =>
    [...main.querySelectorAll('input, select, button')].filter(element => {
      const rect = element.getBoundingClientRect()
      return rect.width > 0 && (rect.left < -1 || rect.right > window.innerWidth + 1)
    }).map(element => element.getAttribute('aria-label') || element.textContent || element.tagName))
  expect(overflow, `controls overflow at ${width}px`).toEqual([])
}

test('sign-in and assignment editor fit phones, tablets and desktops in both languages', async ({ page }) => {
  await page.goto('/')
  for (const width of widths) {
    await page.setViewportSize({ width, height: 900 })
    for (const language of ['TH', 'EN']) {
      await page.getByRole('button', { name: language, exact: true }).click()
      await expectPageFits(page, width)
    }
  }
  await page.getByRole('button', { name: /Explore as instructor/ }).click()
  await page.getByRole('button', { name: /Manage classroom/ }).click()
  await page.locator('summary').filter({ hasText: 'Create assignment' }).click()
  for (const width of widths) {
    await page.setViewportSize({ width, height: 900 })
    for (const language of ['TH', 'EN']) {
      await page.getByRole('button', { name: language, exact: true }).click()
      await expectPageFits(page, width)
    }
  }
  await page.setViewportSize({ width: 390, height: 900 })
  await page.screenshot({ path: 'test-results/responsive-instructor.png', fullPage: true })
})

test('confirmation stays within a narrow or short viewport with reachable actions', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.goto('/')
  await page.getByRole('button', { name: 'EN', exact: true }).click()
  await page.getByRole('button', { name: /Explore as instructor/ }).click()
  await page.getByRole('button', { name: /Manage classroom/ }).click()
  await page.getByText('Move student between groups', { exact: true }).click()
  const students = page.getByLabel('Choose student')
  await expect.poll(() => students.locator('option').count()).toBeGreaterThan(1)
  await students.selectOption({ index: 1 })
  await page.getByLabel('Target group').selectOption({ index: 2 })
  for (const viewport of [{ width: 320, height: 568 }, { width: 740, height: 200 }]) {
    await page.setViewportSize(viewport)
    await page.getByRole('button', { name: 'Move', exact: true }).click()
    const dialog = page.getByRole('alertdialog')
    await expect(dialog).toBeVisible()
    await expect(dialog).toHaveCSS('animation-name', 'none')
    const bounds = await dialog.boundingBox()
    expect(bounds!.x).toBeGreaterThanOrEqual(0)
    expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(viewport.width)
    expect(bounds!.y).toBeGreaterThanOrEqual(0)
    expect(bounds!.y + bounds!.height).toBeLessThanOrEqual(viewport.height)
    const cancel = dialog.getByRole('button', { name: 'Cancel', exact: true })
    await cancel.scrollIntoViewIfNeeded()
    await expect(cancel).toBeInViewport()
    await page.screenshot({ path: `test-results/responsive-dialog-${viewport.width}.png` })
    await cancel.click()
  }
})

test('student evaluations and scores remain usable at every supported width', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'EN', exact: true }).click()
  await page.getByRole('button', { name: /Explore as student/ }).click()
  await expect(page.getByTestId('pair-candidates').first()).toBeVisible()
  await page.locator('summary').filter({ hasText: 'Scores and coverage' }).first().click()
  await expect(page.locator('table').first()).toBeVisible()
  for (const width of widths) {
    await page.setViewportSize({ width, height: 900 })
    for (const language of ['TH', 'EN']) {
      await page.getByRole('button', { name: language, exact: true }).click()
      await expectPageFits(page, width)
    }
  }
  await page.setViewportSize({ width: 320, height: 900 })
  const scores = page.getByRole('region', { name: 'Scores and coverage', exact: true }).first()
  await scores.scrollIntoViewIfNeeded()
  await scores.focus()
  await expect(scores).toBeFocused()
  expect(await scores.evaluate(element => element.scrollWidth > element.clientWidth)).toBe(true)
  await scores.evaluate(element => { element.scrollLeft = element.scrollWidth })
  expect(await scores.evaluate(element => element.scrollLeft)).toBeGreaterThan(0)
  await page.screenshot({ path: 'test-results/responsive-student.png', fullPage: true })
})
