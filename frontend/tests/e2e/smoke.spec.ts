import { expect, test } from '@playwright/test'

/**
 * The first gate after a deploy: did we ship a page that renders at all?
 *
 * These run against the landing page with no backend, which is the state a
 * broken API deploy leaves users in — so they check that the page degrades
 * instead of going blank.
 */

test('the landing page loads and identifies itself as PairEval', async ({ page }) => {
  await page.goto('/')

  await expect(page).toHaveTitle(/PairEval/)
  await expect(page.getByTestId('brand')).toHaveText('PairEval')
})

test('the main navigation is visible', async ({ page }) => {
  await page.goto('/')

  // Prefer the role over the testid: it is what a screen-reader user reaches
  // for too, so this assertion covers FR-A11Y-05 at the same time.
  await expect(page.getByRole('navigation', { name: 'Main' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Features' })).toBeVisible()
})

test('the main call to action is reachable', async ({ page }) => {
  await page.goto('/')

  await expect(page.getByTestId('main-cta')).toBeVisible()
  await expect(page.getByTestId('main-cta')).toBeEnabled()
})

test('the page still renders when the backend is unreachable', async ({ page }) => {
  await page.route('**/health', (route) => route.abort())
  await page.route('**/classrooms/**', (route) => route.abort())

  await page.goto('/')

  await expect(page.getByTestId('backend-status')).toHaveText('offline')
  await expect(page.getByTestId('classroom-list-empty')).toBeVisible()
})

test('the layout works on a 320px viewport', async ({ page }) => {
  // NFR-COMPAT-02: every function must work at 320px or wider.
  await page.setViewportSize({ width: 320, height: 720 })
  await page.goto('/')

  await expect(page.getByTestId('main-cta')).toBeVisible()

  const overflows = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  )
  expect(overflows, 'the page scrolls sideways at 320px').toBe(false)
})
