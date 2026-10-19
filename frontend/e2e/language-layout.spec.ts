import { expect, test } from '@playwright/test'

async function typographyReady(page: import('@playwright/test').Page) {
  await page.evaluate(() => document.fonts.ready)
}

test('language controls stay in place when the translated sign-out label changes', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'EN', exact: true }).click()
  await page.getByRole('button', { name: /Explore as instructor/ }).click()
  await expect(page.getByRole('button', { name: /Sign out/ })).toBeVisible()
  for (const width of [390, 1280]) {
    await page.setViewportSize({ width, height: 900 })
    await page.getByRole('button', { name: 'TH', exact: true }).click()
    await typographyReady(page)
    const thai = await page.locator('.language-switch').boundingBox()
    await page.getByRole('button', { name: 'EN', exact: true }).click()
    await typographyReady(page)
    const english = await page.locator('.language-switch').boundingBox()
    console.log(`language control at ${width}px: TH=${JSON.stringify(thai)} EN=${JSON.stringify(english)}`)
    expect(Math.abs(english!.x - thai!.x)).toBeLessThanOrEqual(1)
    expect(Math.abs(english!.y - thai!.y)).toBeLessThanOrEqual(1)
    expect(english!.height).toBe(thai!.height)
  }
})

test('sign-in panel and role controls keep their positions across languages', async ({ page }) => {
  await page.goto('/')
  for (const width of [390, 1280]) {
    await page.setViewportSize({ width, height: 900 })
    await page.getByRole('button', { name: 'TH', exact: true }).click()
    await typographyReady(page)
    const positions = () => page.locator('.login-panel, .demo-options').evaluateAll(elements => elements.map(element => {
      const box = element.getBoundingClientRect()
      return { x: box.x, y: box.y, width: box.width, height: box.height }
    }))
    const thai = await positions()
    await page.getByRole('button', { name: 'EN', exact: true }).click()
    await typographyReady(page)
    const english = await positions()
    console.log(`sign-in layout at ${width}px: TH=${JSON.stringify(thai)} EN=${JSON.stringify(english)}`)
    for (let i = 0; i < thai.length; i++) {
      expect(Math.abs(english[i].x - thai[i].x)).toBeLessThanOrEqual(1)
      expect(Math.abs(english[i].y - thai[i].y)).toBeLessThanOrEqual(1)
      expect(Math.abs(english[i].height - thai[i].height)).toBeLessThanOrEqual(1)
    }
  }
})

test('the system name stays on one line without moving the brand when language changes', async ({ page }) => {
  await page.goto('/')
  for (const width of [390, 800, 1280]) {
    await page.setViewportSize({ width, height: 900 })
    let previousHeight: number | undefined
    for (const language of ['TH', 'EN', 'TH']) {
      await page.getByRole('button', { name: language, exact: true }).click()
      await typographyReady(page)
      const measurements = await page.locator('.brand').evaluate(brand => {
        const description = brand.querySelector('small')!
        const range = document.createRange()
        range.selectNodeContents(description)
        const lines = [...range.getClientRects()]
        return {
          lines: new Set(lines.map(line => Math.round(line.top))).size,
          height: brand.getBoundingClientRect().height,
          fits: description.scrollWidth <= description.clientWidth,
        }
      })
      expect(measurements.lines).toBe(1)
      expect(measurements.fits).toBe(true)
      if (previousHeight !== undefined) expect(Math.abs(measurements.height - previousHeight)).toBeLessThanOrEqual(1)
      previousHeight = measurements.height
    }
  }
})
