const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "")

export type Classroom = { id: number; name: string; instructor_emails: string }
export type CurrentUser = { email: string; is_instructor: boolean; classroom_ids: number[] }
export type RosterImportResult = { imported: number; errors: string[] }
export type CriterionInput = { name: string; weight: number }
export type AssignmentSetup = {
  title: string
  group_score: number
  individual_score: number
  group_participation_max: number
  individual_participation_max: number
  instructor_weight: number
  group_deadline: string | null
  individual_deadline: string | null
  group_criteria: CriterionInput[]
  individual_criteria: CriterionInput[]
}
export type Assignment = { id: number; title: string; published_at: string | null }
export type Criterion = { id: number; assignment_id: number; name: string; weight: number; is_group: boolean }
export type Group = { id: number; name: string; classroom_id: number }
export type Student = { id: number; email: string; group_name: string | null; group_id: number | null; classroom_id: number }
export type InstructorPair = { pair_id: number; section: string; criterion: string; left: string; right: string; choice: number | null; is_open: boolean }
export type EvaluationPair = {
  id: number; criterion: string; left: string; right: string
  draft_choice: number | null; submitted_choice: number | null
}
export type EvaluationPage = {
  assignment_id: number; section: string; deadline: string | null
  is_open: boolean; submitted_at: string | null; pairs: EvaluationPair[]
}
export type StudentScore = {
  student_id: number; email: string; group_name: string | null
  group_work_score: number | null; individual_work_score: number | null
  group_participation_score: number | null; individual_participation_score: number | null
}
export type AssignmentReport = {
  assignment_id: number; title: string; students: StudentScore[]
  groups: { group_id: number; name: string; work_score: number | null }[]
  coverage: { section: string; criterion: string; left_id: number; right_id: number; votes: number; missing_to_five: number }[]
  criterion_scores: { criterion_id: number; criterion: string; section: string; item_id: number; weighted_score: number | null; effective_votes: number }[]
  group_final: boolean; individual_final: boolean
}
let credential: string | null = null

export function setCredential(value: string): void {
  credential = value
}

function authHeaders(): HeadersInit {
  if (!credential) throw new Error("Sign in required")
  return { Authorization: `Bearer ${credential}` }
}

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null)
    const detail = body && typeof body === 'object' && 'detail' in body && typeof body.detail === 'string'
      ? body.detail
      : `API request failed: ${response.status}`
    throw new Error(detail)
  }
  return response.json() as Promise<T>
}

export async function getHealth(): Promise<{ status: string }> {
  const response = await fetch(`${API_BASE}/health`)
  return readJson<{ status: string }>(response)
}

export async function getClassrooms(): Promise<Classroom[]> {
  const response = await fetch(`${API_BASE}/classrooms/`, { headers: authHeaders() })
  return readJson<Classroom[]>(response)
}

export async function getMe(): Promise<CurrentUser> {
  const response = await fetch(`${API_BASE}/me`, { headers: authHeaders() })
  return readJson<CurrentUser>(response)
}

export async function createClassroom(name: string): Promise<Classroom> {
  const response = await fetch(`${API_BASE}/classrooms/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify({ name, instructor_emails: "" }),
  })
  return readJson<Classroom>(response)
}

export async function inviteInstructor(classroomId: number, email: string): Promise<Classroom> {
  const response = await fetch(`${API_BASE}/classrooms/${classroomId}/instructors`, {
    method: 'POST', headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ email }),
  })
  return readJson<Classroom>(response)
}

export async function removeInstructor(classroomId: number, email: string): Promise<Classroom> {
  const response = await fetch(`${API_BASE}/classrooms/${classroomId}/instructors/${encodeURIComponent(email)}`, {
    method: 'DELETE', headers: authHeaders(),
  })
  return readJson<Classroom>(response)
}

export async function importRoster(classroomId: number, csvText: string): Promise<RosterImportResult> {
  const response = await fetch(`${API_BASE}/classrooms/${classroomId}/roster/import`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ csv_text: csvText }),
  })
  return readJson<RosterImportResult>(response)
}

export async function getAssignments(classroomId: number): Promise<Assignment[]> {
  const response = await fetch(`${API_BASE}/assignments/?classroom_id=${classroomId}`, { headers: authHeaders() })
  return readJson<Assignment[]>(response)
}

export async function getCriteria(assignmentId: number): Promise<Criterion[]> {
  const response = await fetch(`${API_BASE}/assignments/${assignmentId}/criteria`, { headers: authHeaders() })
  return readJson<Criterion[]>(response)
}

export async function getGroups(classroomId: number): Promise<Group[]> {
  const response = await fetch(`${API_BASE}/groups/?classroom_id=${classroomId}`, { headers: authHeaders() })
  return readJson<Group[]>(response)
}

export async function getStudents(classroomId: number): Promise<Student[]> {
  const response = await fetch(`${API_BASE}/students/?classroom_id=${classroomId}&limit=500`, { headers: authHeaders() })
  return readJson<Student[]>(response)
}

export async function reassignStudent(classroomId: number, studentId: number, groupId: number): Promise<{ changed_pairs: number; notified_students: number }> {
  const response = await fetch(`${API_BASE}/classrooms/${classroomId}/students/${studentId}/group`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ group_id: groupId }),
  })
  return readJson<{ changed_pairs: number; notified_students: number }>(response)
}

export async function getReassignments(classroomId: number): Promise<{ id: number; student_id: number; old_group_id: number; new_group_id: number; changed_at: string }[]> {
  const response = await fetch(`${API_BASE}/classrooms/${classroomId}/reassignments`, { headers: authHeaders() })
  return readJson(response)
}

export async function getNotifications(classroomId: number): Promise<{ id: number; message: string; created_at: string }[]> {
  const response = await fetch(`${API_BASE}/classrooms/${classroomId}/notifications`, { headers: authHeaders() })
  return readJson(response)
}

export async function addInstructorPair(assignmentId: number, data: { criteria_id: number; left_id: number; right_id: number; instructor_email: string }): Promise<{ pair_id: number }> {
  const response = await fetch(`${API_BASE}/assignments/${assignmentId}/instructor-pairs`, {
    method: 'POST', headers: { 'Content-Type': 'application/json', ...authHeaders() }, body: JSON.stringify(data),
  })
  return readJson<{ pair_id: number }>(response)
}

export async function getInstructorPairs(assignmentId: number): Promise<InstructorPair[]> {
  const response = await fetch(`${API_BASE}/assignments/${assignmentId}/instructor-pairs`, { headers: authHeaders() })
  return readJson<InstructorPair[]>(response)
}

export async function saveInstructorVote(assignmentId: number, pairId: number, choice: number): Promise<void> {
  const response = await fetch(`${API_BASE}/assignments/${assignmentId}/instructor-pairs/${pairId}/vote`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json', ...authHeaders() }, body: JSON.stringify({ choice }),
  })
  await readJson(response)
}

export async function createAssignment(classroomId: number, setup: AssignmentSetup): Promise<Assignment> {
  const response = await fetch(`${API_BASE}/classrooms/${classroomId}/assignments`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(setup),
  })
  return readJson<Assignment>(response)
}

export async function getAssignmentSetup(assignmentId: number): Promise<AssignmentSetup> {
  const response = await fetch(`${API_BASE}/assignments/${assignmentId}/setup`, { headers: authHeaders() })
  return readJson<AssignmentSetup>(response)
}

export async function updateAssignmentSetup(assignmentId: number, setup: AssignmentSetup): Promise<Assignment> {
  const response = await fetch(`${API_BASE}/assignments/${assignmentId}/setup`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(setup),
  })
  return readJson<Assignment>(response)
}

export async function previewAssignment(assignmentId: number): Promise<{ pair_assignments: number }> {
  const response = await fetch(`${API_BASE}/assignments/${assignmentId}/preview`, { headers: authHeaders() })
  return readJson<{ pair_assignments: number }>(response)
}

export async function publishAssignment(assignmentId: number): Promise<{ pair_assignments: number }> {
  const response = await fetch(`${API_BASE}/assignments/${assignmentId}/publish`, {
    method: 'POST', headers: authHeaders(),
  })
  return readJson<{ pair_assignments: number }>(response)
}

export async function getEvaluation(assignmentId: number, section: string): Promise<EvaluationPage> {
  const response = await fetch(`${API_BASE}/assignments/${assignmentId}/evaluation/${section}`, { headers: authHeaders() })
  return readJson<EvaluationPage>(response)
}

export async function saveEvaluationDraft(assignmentId: number, section: string, changes: { pair_id: number; choice: number | null }[]): Promise<EvaluationPage> {
  const response = await fetch(`${API_BASE}/assignments/${assignmentId}/evaluation/${section}/draft`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ changes }),
  })
  return readJson<EvaluationPage>(response)
}

export async function submitEvaluation(assignmentId: number, section: string): Promise<{ submission_id: number; answered: number; assigned: number }> {
  const response = await fetch(`${API_BASE}/assignments/${assignmentId}/evaluation/${section}/submit`, {
    method: 'POST', headers: authHeaders(),
  })
  return readJson<{ submission_id: number; answered: number; assigned: number }>(response)
}

export async function getMyScores(assignmentId: number): Promise<StudentScore> {
  const response = await fetch(`${API_BASE}/assignments/${assignmentId}/my-scores`, { headers: authHeaders() })
  return readJson<StudentScore>(response)
}

export async function getAssignmentReport(assignmentId: number): Promise<AssignmentReport> {
  const response = await fetch(`${API_BASE}/assignments/${assignmentId}/report`, { headers: authHeaders() })
  return readJson<AssignmentReport>(response)
}

export async function downloadReportCsv(assignmentId: number, sheet: 'groups' | 'students' | 'pairs'): Promise<void> {
  const response = await fetch(`${API_BASE}/assignments/${assignmentId}/report/${sheet}.csv`, { headers: authHeaders() })
  if (!response.ok) throw new Error(`Export failed: ${response.status}`)
  const url = URL.createObjectURL(await response.blob())
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `assignment-${assignmentId}-${sheet}.csv`
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}

export async function downloadReportXlsx(assignmentId: number): Promise<void> {
  const response = await fetch(`${API_BASE}/assignments/${assignmentId}/report.xlsx`, { headers: authHeaders() })
  if (!response.ok) throw new Error(`Export failed: ${response.status}`)
  const url = URL.createObjectURL(await response.blob())
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `assignment-${assignmentId}.xlsx`
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}
