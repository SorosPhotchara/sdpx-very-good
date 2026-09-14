# Unit: Roster Import

## Purpose

Get a class list out of a spreadsheet and into the system without silently
losing anybody, duplicating anybody, or handing a formula to whoever opens the
export.

## Responsibilities

- Parse a roster CSV (`email`, `group_name`, optional `student_id`,
  `display_name`), matching headers case-insensitively.
- Normalise email addresses to one canonical form (FR-AUTH-03): lowercase and
  remove `+tag`. Whether dots are removed too is still open (see below).
- Validate every row and either accept the whole file or reject the whole file
  (FR-CLASS-02).
- Report every problem at once, by the row number Excel shows (header = row 1).
- Neutralise spreadsheet formula injection on the way in and out (FR-SEC-04).

## NOT Responsible For

- Writing rows to the database, and creating `PENDING` users (FR-CLASS-04) →
  `POST /api/classrooms/{classroomId}/roster:import`
- Deciding who is allowed to import → the authorization layer
- Group sizing advice for pairing → **Pairing Engine**

## Dependencies

- **Depends on:** the standard library only (`csv`, `re`). No I/O — it takes
  text and returns a result object, so a 100-row failure case is a unit test.
- **Used by:** `POST /api/classrooms/{classroomId}/roster:import`
  (`docs/openapi.yaml`, US-CLASS-01).

## Key Business Rules

> No code exists yet. Each rule becomes a test in WS-03; the name on the right
> is the test name to use. The full list of cases is in US-CLASS-01 in
> `docs/user-stories.md`.

| Rule | Planned test |
|---|---|
| A roster address and a login address for the same person match (FR-AUTH-03) | `test_roster_address_and_login_address_resolve_to_the_same_person` |
| Case and `+tag` suffixes are folded away | `test_case_and_plus_tags_are_folded_away` |
| An implausible address is rejected rather than stored | `test_implausible_addresses_are_rejected` |
| Headers match regardless of case or padding (FR-CLASS-01, US-CLASS-01 AC1) | `test_header_matching_ignores_case_and_surrounding_space` |
| **One bad row rejects the entire file (FR-CLASS-02)** | `test_one_bad_row_rejects_the_entire_file` |
| A rejection names the Excel row number — row 42 in a 100-row file (US-CLASS-01 AC2) | `test_a_rejected_file_names_the_row_that_broke_it` |
| Every error is reported at once, not one upload at a time | `test_every_error_is_reported_at_once_rather_than_one_upload_at_a_time` |
| Duplicates are detected **after** normalisation (FR-CLASS-03) | `test_duplicate_emails_are_caught_after_normalisation_not_before` |
| An empty `group_name` is an error, never a default | `test_an_empty_group_name_is_an_error_not_a_default` |
| A blank line is skipped, and later row numbers still match Excel | `test_blank_lines_are_skipped_without_shifting_row_numbers` |
| A missing required header stops the import immediately | `test_a_missing_required_header_stops_the_import_immediately` |
| Cells Excel would execute are defused (FR-SEC-04) | `test_cells_that_excel_would_execute_are_defused` |
| A formula in a group name survives import as inert text | `test_a_formula_in_a_group_name_survives_import_as_inert_text` |

## Notes for implementation

- **Atomic is not pedantry.** A partial import is worse than no import, because
  nothing downstream notices. The pairing engine will happily build a balanced
  allocation for a class that is missing the students whose rows failed, and
  nobody finds out until those students cannot log in — by which time the pairs
  are frozen.
- **Escape on import, not only on export.** Defusing a cell as it enters means
  no future export path has to remember to do it.
- **Uniqueness is enforced twice.** This parser reports duplicates inside one
  file; `UNIQUE (email_normalized)` on `user` in `docs/erd.md` stops two
  separate imports from colliding.

## Key Stories

- US-CLASS-01 — Create a classroom and import the roster from CSV

## Bolt Type

- [ ] DDD Construction
- [x] **Simple Construction** — parsing and validation. The rules are numerous
      but shallow; there is no domain model underneath.

## Human Checkpoint

Can this be built without knowing how pairing or scoring work? **Yes.** It ends
at a validated list of rows. It does not know what a comparison is.

## Open Questions

- **Dots in email addresses** — FR-AUTH-03 says to remove dots only for Gmail,
  but its own example removes them for a university address too. Removing them
  everywhere can merge two different people. Waiting for the instructor (see
  US-AUTH-01 in `docs/user-stories.md`).
- **Q4** — is a group with fewer than 2 members an error or a warning?
- **Q5** — what happens when a roster is imported into a classroom that already
  has one? The API refuses with `409 ROSTER_ALREADY_EXISTS` for now (provisional).
- **Q6** — emails outside the classroom's allowed domains, or belonging to staff
  of the same classroom.
- **OQ-4** (PRD §17) — students who withdraw mid-semester.
- **FR-CLASS-05** (upsert with a diff preview) is out of scope for US-CLASS-01.
