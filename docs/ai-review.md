# AI review for WS-08

Target: `backend/app/reports.py::assignment_report` (reviewed 5 October 2026). This is a review backlog; no code was changed for this homework.

Prompt used:

> Review this code and list ALL problems you find. Be specific about code smells, naming, missing error handling, performance problems, and security issues. Rate each issue High / Medium / Low severity, and say why it matters.

## Findings to verify before refactoring

| Severity | Evidence | Why it matters |
|---|---|---|
| High | `item.choices` is read for each latest submission; the relationship in `models.py` has no eager loading. | A report can issue one extra SQL query per submission (N+1), making response time grow with class size. Confirm by counting SQL statements for small and large classes. |
| Medium | The function loads all students, groups, criteria, pairs and submissions into memory before computing one student's `/my-scores`. | Student requests pay the cost of a whole-class report. Large classes increase latency and memory use. Measure `/my-scores` separately from the teacher report. |
| Medium | Each criterion scans the full `pairs` list, then each student scans `groups` and counts `students` again. | Repeated work grows roughly with criteria × pairs plus students². Profile with representative classroom sizes. |
| Medium | `latest` relies on ordering by `Submission.id`, then overwrites entries keyed by student and section. | The rule "latest submission" is implicit and tied to insertion order. A timestamp or database query selecting the latest row would state the rule more clearly. Verify concurrent submission behavior first. |
| Medium | One function fetches data, computes scores and participation, builds coverage, and serializes the response. | Changes to one rule can affect several outputs; focused tests and profiling are harder. |
| Low | `submitted` is later updated with instructor votes. | The name no longer describes the contents, making vote precedence easy to misunderstand. |
| Low | Database and relationship-loading errors are not given report-specific context here. | Failures propagate as generic server errors, which makes a slow or broken query harder to locate from application logs. |
| Low | The return annotation is only `dict`, and the result is assembled from nested untyped dictionaries. | Callers cannot reliably see which fields may be `None`; schema changes are easier to miss. |
| Low | The number `5` in `missing_to_five` is embedded inside report assembly. | If the coverage policy changes, this value can disagree with pair allocation. |

Security check: the teacher report route calls `require_owner`, and `/my-scores` checks classroom membership before returning only the matching row. No direct authorization flaw was confirmed in this function. Keep that route boundary covered by tests during WS-08 refactoring.
