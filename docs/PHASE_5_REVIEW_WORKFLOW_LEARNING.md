# ConferenceFlow Phase 5: Reviewer Workflow

## What changed

Phase 5 connects reviewer work to real database records. The reviewer dashboard
now loads only assignments belonging to the signed-in reviewer. It displays the
paper title, paper status, and whether the review is pending or completed.
Counts are calculated from those same records instead of being hardcoded.

Administrators now see assignment, completed-review, and pending-review counts.
The assignment endpoint validates that both selected IDs are integers, that the
paper exists, and that the selected account really has the `reviewer` role.

The review endpoint still uses the existing 1-10 scoring scale. It checks the
assignment belongs to the current reviewer and refuses a second review for the
same assignment. Review comments and individual scores are not displayed on
the public paper pages.

## Important database idea

`review_assignments` is the link between a paper and a reviewer. A review points
to an assignment, not merely to a paper. This makes it possible to answer
"which reviewer submitted this review?" without trusting browser input.

The application checks for duplicate reviews before inserting. A future,
approved migration could also add `UNIQUE (assignment_id)` as a database-level
backstop. That migration is intentionally not applied in this phase.

## Request flow

1. A reviewer requests `/reviewer_dashboard`.
2. Flask reads the reviewer ID from the session.
3. A parameterized SQL query filters assignments by that ID.
4. Flask passes rows to the Jinja template.
5. The browser renders the table and status cards.

Submitting a review follows the same pattern, with server-side validation,
ownership checking, a duplicate check, and a transaction commit.

## Beginner notes

- A dashboard statistic is trustworthy only when it comes from current data.
- A foreign key identifies a related row; it does not automatically prevent
  every business duplicate.
- A validation check at the application layer improves the user experience.
- A unique constraint is still useful because two simultaneous requests can
  pass an application check at the same time.
- Reviewer comments are confidential workflow data and should not be shown to
  paper authors.
