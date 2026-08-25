# Unit: Roster Import

## Purpose

Get a class list out of a spreadsheet and into the system without silently
losing anybody, duplicating anybody, or handing a formula to whoever opens the
export.

## Responsibilities

- Parse a roster CSV (`email`, `group_name`, optional `student_id`,
  `display_name`), matching headers case-insensitively.
- Normalise email addresses to a single canonical form (FR-AUTH-03).
- Validate every row and either accept the whole file or reject the whole file
  (FR-CLASS-02).
- Report every problem at once, by file line number.
- Warn — but not fail — on groups with fewer than 2 members.
- Neutralise spreadsheet formula injection on the way in and out (FR-SEC-04).

## NOT Responsible For

- Writing rows to the database → `crud` / the import route
- Creating `PENDING` users or activating them on first login (FR-CLASS-04)
- Deciding who is allowed to import → authorization layer
- Group *sizing* advice for pairing → **Pairing Engine** (`individual_plan`)

## Dependencies

- **Depends on:** the standard library only (`csv`, `re`). No I/O — it takes
  text and returns a result object, so a 100-row failure case is a unit test.
- **Used by:** the roster import route (not built yet), US-02

## Key Business Rules

| Rule | Test |
|---|---|
| A roster address and a login address for the same person match (FR-AUTH-03) | `test_roster_address_and_login_address_resolve_to_the_same_person` |
| Case, dots in the local part, and `+tag` suffixes are all folded away | `test_case_dots_and_plus_tags_are_folded_away` |
| An implausible address is rejected rather than stored | `test_implausible_addresses_are_rejected` |
| Headers match regardless of case or padding (FR-CLASS-01) | `test_header_matching_ignores_case_and_surrounding_space` |
| **One bad row rejects the entire file (FR-CLASS-02)** | `test_one_bad_row_rejects_the_entire_file` |
| A rejection names the offending file line | `test_a_rejected_file_names_the_line_that_broke_it` |
| Every error is reported at once, not one upload at a time | `test_every_error_is_reported_at_once_rather_than_one_upload_at_a_time` |
| Duplicates are detected **after** normalisation (FR-CLASS-03) | `test_duplicate_emails_are_caught_after_normalisation_not_before` |
| An empty `group_name` is an error, never a default | `test_an_empty_group_name_is_an_error_not_a_default` |
| A one-member group warns but still imports (FR-CLASS-03) | `test_a_group_with_one_member_warns_but_still_imports` |
| A blank trailing line is not a broken row | `test_blank_trailing_lines_are_not_treated_as_broken_rows` |
| A missing required header stops the import immediately | `test_a_missing_required_header_stops_the_import_immediately` |
| Cells Excel would execute are defused (FR-SEC-04) | `test_cells_that_excel_would_execute_are_defused` |
| A formula in a group name survives import as inert text | `test_a_formula_in_a_group_name_survives_import_as_inert_text` |

## Design notes worth keeping

### Atomic is not pedantry

A partial import is worse than no import, because nothing downstream notices.
The pairing engine will happily generate a perfectly balanced allocation for a
class that is missing the eleven students whose rows failed — and nobody finds
out until those eleven cannot log in, by which time the pairs are frozen.

### Two classes of problem, two behaviours

| Problem | Behaviour | Why |
|---|---|---|
| Malformed email, duplicate email, empty group | **Error** — reject the file | The row cannot become a usable student |
| Group with fewer than 2 members | **Warning** — import anyway | Legal (a partner dropped the course) but it disables individual evaluation for that group (§8.3), so the instructor has to know *before* publishing |

### Normalisation is deliberately aggressive

Dots are stripped from the local part for every domain, not just Gmail. That is
what FR-AUTH-03's own example requires — it uses `uni.ac.th`. It is aggressive
enough to collapse two genuinely different addresses at a provider that treats
dots as significant; accepted, because within one university domain the risk of
a missed login is larger than the risk of a collision, and a collision is
*reported* as a duplicate rather than silently merged.

### Escaping happens on import, not only export

A cell is defused as it enters. Escaping only on the way out means every future
export path has to remember to do it, and one that forgets ships a live payload
into an instructor's spreadsheet.

## Key Stories

- US-02 — Import a roster from CSV

## Bolt Type

- [ ] DDD Construction
- [x] **Simple Construction** — parsing and validation. The rules are numerous
      but shallow; there is no domain model underneath.

## Human Checkpoint

Can this be built without knowing how pairing or scoring work? **Yes.** It ends
at a validated list of rows. It does not know what a comparison is.

## Open Questions

- **FR-CLASS-05** (upsert with a diff preview) is not implemented. Re-importing
  currently means a fresh file, so a mid-semester group change cannot be made
  without deciding what happens to comparisons already submitted (DR-02).
- **OQ-4** — students who withdraw mid-semester. The default is to mark them
  `WITHDRAWN`, drop them from the calculation, and reassign their outstanding
  pairs. None of that is built, and it needs the registrar's answer first.
- The `email_normalized` column that would enforce uniqueness in the database
  does not exist yet (TD-01 territory) — the check currently lives only in this
  parser, so two separate imports could still collide.
