import { expect, test } from '@playwright/test'

test('mobile room navigation keeps creation on demand and desktop keeps it visible', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await page.getByRole('button', { name: 'EN', exact: true }).click()
  await page.getByRole('button', { name: /Explore as instructor/ }).click()
  const trigger = page.getByRole('button', { name: '+ New room', exact: true })
  const input = page.getByLabel('Add classroom')
  await expect(trigger).toHaveAttribute('aria-expanded', 'false')
  await expect(input).toBeHidden()
  await trigger.click()
  await expect(input).toBeVisible()
  await input.fill('Mobile classroom')
  await expect(page.getByRole('button', { name: 'Create classroom', exact: true })).toBeEnabled()
  await page.getByRole('button', { name: 'Close', exact: true }).click()
  await expect(input).toBeHidden()
  await page.setViewportSize({ width: 1280, height: 900 })
  await expect(input).toBeVisible()
  await expect(input).toHaveValue('Mobile classroom')
  await expect(page.locator('.classroom-create-toggle')).toBeHidden()
})

test('layout contains long classroom names while resizing through intermediate widths', async ({ page }) => {
  await page.route('**/classrooms/', async route => {
    if (route.request().method() !== 'GET') return route.continue()
    const response = await route.fetch()
    const classrooms = await response.json()
    classrooms[0].name = 'A classroom with a long project name and reference ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    await route.fulfill({ response, json: classrooms })
  })
  await page.goto('/')
  await page.getByRole('button', { name: 'EN', exact: true }).click()
  await page.getByRole('button', { name: /Explore as instructor/ }).click()
  await expect(page.locator('.page-heading h1')).toBeVisible()
  for (const width of [280, 320, 375, 430, 600, 700, 701, 768, 843, 900, 1000, 1099, 1100, 1280, 1440, 1920, 2560]) {
    await page.setViewportSize({ width, height: 900 })
    await page.evaluate(() => document.fonts.ready)
    expect(await page.evaluate(() => document.documentElement.scrollWidth), `overflow at ${width}px`).toBeLessThanOrEqual(width)
    const heading = await page.locator('.page-heading h1').boundingBox()
    expect(heading!.x + heading!.width).toBeLessThanOrEqual(width)
  }
})
