import { expect, test } from '@playwright/test'

test('deduplicates strict-mode reads and ignores stale results after resource changes', async ({ page }) => {
  let release!: () => void
  const pending = new Promise<void>(resolve => { release = resolve })
  let firstReads = 0
  await page.route('**/resource/first', async route => { firstReads++; await pending; await route.fulfill({ body: 'Old classroom' }) })
  await page.route('**/resource/second', route => route.fulfill({ body: 'Current classroom' }))
  await page.goto('/e2e/resource-harness.html')
  await expect(page.locator('output')).toHaveText('Loading')
  await expect.poll(() => firstReads).toBe(1)
  await page.getByRole('button', { name: 'Switch' }).click()
  await expect(page.locator('output')).toHaveText('Current classroom')
  const oldResponse = page.waitForResponse('**/resource/first')
  release()
  await oldResponse
  await page.unrouteAll({ behavior: 'wait' })
  await expect(page.locator('output')).toHaveText('Current classroom')
})

test('shows load failures and retries instead of displaying an empty result', async ({ page }) => {
  let attempts = 0
  await page.route('**/resource/first', route => route.fulfill(++attempts === 1 ? { status: 503 } : { body: 'Recovered classroom' }))
  await page.goto('/e2e/resource-harness.html')
  await expect(page.locator('output')).toHaveText('Temporary failure')
  await page.getByRole('button', { name: 'Retry' }).click()
  await expect(page.locator('output')).toHaveText('Recovered classroom')
  expect(attempts).toBe(2)
})

test('Google renewal prompts once and sign-out cancels automatic reauthentication', async ({ page }) => {
  await page.route('https://accounts.google.com/gsi/client', route => route.fulfill({ body: '', contentType: 'application/javascript' }))
  await page.addInitScript(() => {
    const state = { initializations: 0, prompts: 0, cancellations: 0, disabled: 0, callback: (_response: { credential: string }) => {} }
    Object.assign(window, { googleTest: state, google: { accounts: { id: {
      initialize(options: { callback: typeof state.callback }) { state.initializations++; state.callback = options.callback },
      renderButton(element: HTMLElement) { element.innerHTML = '<button>Google sign-in stub</button>' },
      prompt() { state.prompts++ }, cancel() { state.cancellations++ }, disableAutoSelect() { state.disabled++ },
    } } } })
  })
  await page.goto('/e2e/resource-harness.html?google')
  await expect(page.getByTestId('google-sign-in')).toBeVisible()
  await expect.poll(() => page.evaluate(() => (window as any).googleTest.initializations)).toBe(1)
  await page.getByRole('button', { name: 'Renew', exact: true }).click()
  await expect.poll(() => page.evaluate(() => (window as any).googleTest.prompts)).toBe(1)
  await page.evaluate(() => (window as any).googleTest.callback({ credential: 'renewed-token' }))
  await expect(page.locator('output')).toHaveText('renewed-token')
  await page.getByRole('button', { name: 'Sign out', exact: true }).click()
  await page.evaluate(() => (window as any).googleTest.callback({ credential: 'late-token' }))
  await expect(page.locator('output')).toHaveText('Signed out')
  expect(await page.evaluate(() => (window as any).googleTest.disabled)).toBe(1)
  expect(await page.evaluate(() => (window as any).googleTest.cancellations)).toBeGreaterThan(0)
})
