import { expect, test } from '@playwright/test'

test('loads only the first evaluation on sign-in, then loads another when opened', async ({ page }) => {
  const evaluations: string[] = []
  await page.route('**/api/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    const json = (value: unknown) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(value) })
    if (path === '/api/health') return json({ status: 'ok' })
    if (path === '/api/me') return json({ email: 'student@example.edu', is_instructor: false, is_admin: false, picture_url: null, classroom_ids: [1] })
    if (path === '/api/classrooms/') return json([{ id: 1, name: 'Test room', instructor_emails: '' }])
    if (path === '/api/assignments/') return json([1, 2, 3].map(id => ({ id, title: `Assignment ${id}`, published_at: '2026-01-01T00:00:00Z' })))
    if (path.includes('/evaluation/')) {
      evaluations.push(path)
      return json({ assignment_id: Number(path.split('/')[3]), section: path.split('/').at(-1), group_name: 'A', deadline: null, is_open: true, submitted_at: null, pairs: [] })
    }
    if (path.endsWith('/notifications')) return json([])
    return route.fulfill({ status: 404 })
  })

  await page.goto('/')
  await page.getByRole('button', { name: 'EN', exact: true }).click()
  await page.getByRole('button', { name: /Explore as student/ }).click()
  await expect(page.getByText('Assignment 3')).toBeVisible()
  await page.waitForLoadState('networkidle')
  expect(evaluations).toEqual(['/api/assignments/1/evaluation/group'])

  await page.getByText('Assignment 2').locator('..').locator('summary.evaluation-section-summary').first().click()
  await expect.poll(() => evaluations.length).toBe(2)
  expect(evaluations[1]).toBe('/api/assignments/2/evaluation/group')
})
