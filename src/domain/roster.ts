export type RosterRow = {
  email: string;
  groupName: string;
};

export type RosterImportResult = {
  rows: RosterRow[];
  errors: string[];
};

const REQUIRED_HEADERS = ["email", "group_name"] as const;

function normalizeHeader(value: string) {
  return value.trim().toLowerCase().replace(/\s+/g, "_");
}

export function normalizeEmail(value: string) {
  const [localPart, domain] = value.trim().toLowerCase().split("@");
  return `${localPart.split("+")[0]}@${domain}`;
}

function isPlausibleEmail(value: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

export function parseRoster(csvText: string): RosterImportResult {
  const lines = csvText.split(/\r?\n/);
  const headerIndex = lines.findIndex((line) => line.trim().length > 0);
  if (headerIndex === -1) return { rows: [], errors: ["The file is empty"] };

  const headers = lines[headerIndex].split(",").map(normalizeHeader);
  const missingHeaders = REQUIRED_HEADERS.filter(
    (header) => !headers.includes(header),
  );
  if (missingHeaders.length > 0) {
    return {
      rows: [],
      errors: [`Missing required header: ${missingHeaders.join(", ")}`],
    };
  }

  const emailIndex = headers.indexOf("email");
  const groupIndex = headers.indexOf("group_name");
  const errors: string[] = [];
  const rows: RosterRow[] = [];
  const seenEmails = new Set<string>();

  lines.forEach((line, index) => {
    if (index === headerIndex || line.trim() === "") return;
    const cells = line.split(",").map((cell) => cell.trim());
    const rowNumber = index + 1;
    const email = normalizeEmail(cells[emailIndex] ?? "");
    const groupName = cells[groupIndex] ?? "";

    if (!isPlausibleEmail(email)) errors.push(`Row ${rowNumber}: invalid email`);
    if (groupName === "") errors.push(`Row ${rowNumber}: group_name is required`);
    if (seenEmails.has(email)) errors.push(`Row ${rowNumber}: duplicate email`);
    if (email !== "" && isPlausibleEmail(email)) seenEmails.add(email);
    rows.push({ email, groupName });
  });

  return errors.length > 0 ? { rows: [], errors } : { rows, errors: [] };
}

export type PairAssignment = {
  evaluatorEmail: string;
  leftGroup: string;
  rightGroup: string;
};

export function publishRoster(rows: RosterRow[]): PairAssignment[] {
  const groups = [...new Set(rows.map((row) => row.groupName))];
  const assignments: PairAssignment[] = [];

  for (const evaluator of groups) {
    const evaluatorEmail = rows.find((row) => row.groupName === evaluator)?.email;
    if (!evaluatorEmail) continue;
    for (let leftIndex = 0; leftIndex < groups.length - 1; leftIndex += 1) {
      for (let rightIndex = leftIndex + 1; rightIndex < groups.length; rightIndex += 1) {
        const leftGroup = groups[leftIndex];
        const rightGroup = groups[rightIndex];
        if (evaluator === leftGroup || evaluator === rightGroup) continue;
        assignments.push({ evaluatorEmail, leftGroup, rightGroup });
      }
    }
  }

  return assignments;
}