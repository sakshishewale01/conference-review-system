# Phase 6: Decisions and End-to-End Workflow

## Recommendations versus official decisions

A reviewer's `Accepted` recommendation is an opinion, not the conference
decision. An administrator reviews all completed evaluations and explicitly
records either `Accepted` or `Rejected`. The application never averages scores
or copies a recommendation automatically.

An administrator cannot decide while an assigned review is still pending. The
decision form validates its allowlist, requires notes, updates the paper inside
a transaction, and immediately releases the decision to the paper owner.

The original schema had only a paper status. Phase 6 adds proposed fields for
the decision maker, decision notes, and timestamps. The migration is not
automatically applied. Historical papers also need a reviewed ownership
backfill because the original schema did not record authors.

## Ownership and confidentiality

After the migration is applied, each new paper stores `author_id`. Authors see
only their own papers and released status. Reviewers see only papers assigned
to them. Administrators can inspect review identities, scores, and comments.
Authors do not see reviewer identities, comments, or scores.

## Transactions

Submission, assignment, review completion, decision recording, and their
notifications use the same database transaction. If an insert or notification
fails, the connection context manager rolls back the operation and the user
receives a safe error message.

## End-to-end flow

1. An author submits a validated PDF and paper metadata.
2. The paper is stored as `Pending` and the author receives a notification.
3. An administrator assigns eligible reviewers.
4. Assigned reviewers see their own pending assignments.
5. A reviewer submits one authorized review.
6. Administrators receive a completion notification.
7. Once all assignments are complete, an administrator records a decision.
8. The author receives a release notification and can open the protected paper.

## Current limitation

The existing database may not yet contain the Phase 6 columns or notification
table. Apply the reviewed migration in
`database/phase6_decisions_notifications.sql` to a backed-up local database
before using these routes. No migration was run by this phase.
