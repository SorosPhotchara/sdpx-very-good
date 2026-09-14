import { describe, expect, test } from "bun:test";
import { normalizeEmail, parseRoster, publishRoster } from "./roster";

describe("roster import", () => {
  test("normalizes case and plus tags", () => {
    expect(normalizeEmail(" Student+team@Uni.ac.th ")).toBe("student@uni.ac.th");
  });

  test("rejects the entire file when one row is invalid", () => {
    const result = parseRoster(
      "Email, Group Name\nstudent@uni.ac.th, Aurora\nnot-an-email, Nova",
    );

    expect(result.rows).toHaveLength(0);
    expect(result.errors).toEqual(["Row 3: invalid email"]);
  });

  test("reports duplicate emails after normalization", () => {
    const result = parseRoster(
      "email,group_name\nstudent+one@uni.ac.th,Aurora\nSTUDENT@UNI.AC.TH,Nova",
    );

    expect(result.errors).toEqual(["Row 3: duplicate email"]);
  });

  test("publishes every unique pair without assigning an evaluator their own group", () => {
    const rows = [
      { email: "a@uni.ac.th", groupName: "Aurora" },
      { email: "b@uni.ac.th", groupName: "Nova" },
      { email: "c@uni.ac.th", groupName: "Orion" },
    ];

    const assignments = publishRoster(rows);

    expect(assignments).toHaveLength(3);
    expect(assignments.every((assignment) => {
      const evaluatorGroup = rows.find((row) => row.email === assignment.evaluatorEmail)?.groupName;
      return evaluatorGroup !== assignment.leftGroup && evaluatorGroup !== assignment.rightGroup;
    })).toBe(true);
  });
});