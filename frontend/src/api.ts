const API_BASE = "http://localhost:8000"

export async function getHealth() {
  const response = await fetch(`${API_BASE}/health`)
  return response.json()
}

export async function getClassrooms() {
  const response = await fetch(`${API_BASE}/classrooms/`)
  return response.json()
}

export async function createClassroom(name: string) {
  const response = await fetch(`${API_BASE}/classrooms/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ name, instructor_emails: "" }),
  })
  return response.json()
}
