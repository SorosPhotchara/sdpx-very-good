# PairEval domain model

The first local release uses one verified Google email as a person's identity. Instructor eligibility comes from `INSTRUCTOR_EMAILS`. A Classroom stores its assigned instructor emails; a Student row is a classroom membership keyed by `(classroom_id, email)`. The same person may have Student rows in several classrooms. CSV import creates pending memberships; `GET /me` records `activated_at` for all matching memberships on first verified sign-in.

## Evaluation lifecycle

1. An assigned instructor creates an Assignment with Group and/or Individual sections. Each active section has a future deadline, separate work and participation maxima, and criteria whose weights sum to 100%.
2. The instructor may edit the Assignment before publication. Preview calculates pair allocations without writing. Publication requires at least three nonempty groups, saves all eligible pairs, and sets `published_at` in one transaction. An Individual section assigns pairs only within groups of at least three members.
3. A Pair identifies one criterion, two subjects, and one evaluator. A student evaluator is in neither subject group for Group pairs, or is neither subject student for Individual pairs. A targeted instructor Pair names an assigned instructor email. Each eligible subject pair gets five student assignments before load balancing.
4. A student saves DraftChoice rows for their assigned pairs. Submit copies all current drafts for that section into an immutable Submission and SubmissionChoice snapshot. The highest Submission ID for that evaluator, Assignment, and section is the effective snapshot. A later partial snapshot replaces the earlier snapshot for scoring; old snapshots remain for history.
5. A group reassignment is accepted only while every criterion deadline in that classroom is still open. It records a Reassignment, retains Pair rows that still match the recalculated plan, marks changed rows with `superseded_at`, creates replacement pairs, and writes Notifications. Superseded votes stay in history but do not count toward current scores.

## Scores and visibility

Five choices give the left/right subjects these points: `1/0`, `.75/.25`, `.5/.5`, `.25/.75`, `0/1`. Instructor votes multiply both points and effective vote count by `instructor_weight`. For each criterion, each subject's average points is divided by the sum of average points of subjects with votes. The result is multiplied by that criterion's weight and its section work maximum. Subject scores without votes are absent before the section deadline and zero afterward.

Participation is a separate component for each student and section: `participation_max × effective submitted pair answers / assigned pairs`. A student who has not submitted gets zero participation. Groups of fewer than three members are exempt from the Individual participation component. Group work scores belong to a group; the report repeats that group's score in each member's row. Students can read only their own row. Instructors assigned to the Classroom can read the full report, criterion details, coverage, and exports.

### Worked examples

- Group criterion `Quality` has weight 60% and Group work maximum 15. One submitted tie between groups A and B gives each 0.5 average points. Their normalized shares are 0.5 each, so each earns `0.5 × 0.60 × 15 = 4.5` from Quality. Group C has no votes: its interim Quality score is absent; after the Group deadline it is 0. Other Group criteria add their own weighted contributions to each group's work score.
- Individual criterion `Contribution` has weight 100% and Individual work maximum 12. A student vote strongly favors A over B. An instructor vote strongly favors B over A, with `instructor_weight = 2`. A's weighted average is `(1×1 + 0×2)/3 = 1/3`; B's is `(0×1 + 1×2)/3 = 2/3`. The normalized shares stay 1/3 and 2/3, yielding Individual work scores of 4 and 8. This uses the same calculation for Group and Individual subjects.
- A student assigned five Group pairs who submits three in their latest snapshot earns `3/5 × group_participation_max`. With a maximum of 4, that is 2.4 participation points. Saving a draft without submitting earns 0. A later submission with only two answers changes the effective ratio to `2/5`; the earlier snapshot remains in history but no longer affects scores.

## Ownership

Classroom instructor emails are approved by the administrator through the environment allowlist before invitation. Any assigned instructor may manage that Classroom, and the last assigned instructor cannot be removed. No instructor or student API may read another Classroom's roster, pairs, evaluations, or report without matching membership or instructor assignment.
