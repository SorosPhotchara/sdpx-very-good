import type { PairAssignment, RosterRow } from "../domain/roster";

type ApiRosterRow = { email: string; group_name: string };
type ApiPairAssignment = { evaluator_email: string; left_group: string; right_group: string };

export type RosterImportResult = { rows: RosterRow[]; errors: string[] };

export async function importRoster(csvText: string): Promise<RosterImportResult> {
  const response = await fetch("/api/rosters/import", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ csv_text: csvText }),
  });
  if (!response.ok) throw new Error(`Roster import failed: ${response.status}`);

  const body: { rows: ApiRosterRow[]; errors: string[] } = await response.json();
  return {
    rows: body.rows.map((row) => ({ email: row.email, groupName: row.group_name })),
    errors: body.errors,
  };
}

export async function previewRoster(rows: RosterRow[]): Promise<PairAssignment[]> {
  const response = await fetch("/api/rosters/preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      rows: rows.map((row) => ({ email: row.email, group_name: row.groupName })),
    }),
  });
  if (!response.ok) throw new Error(`Roster preview failed: ${response.status}`);

  const body: { assignments: ApiPairAssignment[] } = await response.json();
  return body.assignments.map((assignment) => ({
    evaluatorEmail: assignment.evaluator_email,
    leftGroup: assignment.left_group,
    rightGroup: assignment.right_group,
  }));
}
