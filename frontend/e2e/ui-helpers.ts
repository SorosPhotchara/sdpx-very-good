import { expect, type Page } from '@playwright/test'

export async function createClassroom(page: Page, name: string) {
  await page.getByRole('button', { name: 'New classroom' }).click()
  const dialog = page.getByRole('dialog', { name: 'Create classroom' })
  await expect(dialog).toBeVisible()
  await dialog.getByLabel('Classroom name').fill(name)
  await dialog.getByRole('button', { name: 'Create classroom' }).click()
  await expect(dialog).toHaveCount(0)
}

export async function openAssignmentEditor(page: Page) {
  await page.getByTestId('create-assignment').click()
  const dialog = page.getByTestId('assignment-editor-dialog')
  await expect(dialog).toBeVisible()
  return dialog
}

export async function closeClassroomManager(page: Page) {
  const dialog = page.getByTestId('classroom-tools-dialog')
  await dialog.getByRole('button', { name: 'Close dialog' }).click()
  await expect(dialog).toHaveCount(0)
}
