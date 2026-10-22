# ConferenceFlow Phase 2: Database Design and MySQL Integration

This guide explains the current ConferenceFlow database design, how Flask
uses MySQL, and which improvements are proposed for a future migration.
The proposed schema changes in this document have **not** been applied.

## 1. Why ConferenceFlow needs a database

A database stores application information so it remains available after the
Flask process stops. ConferenceFlow needs persistent storage for users,
submitted papers, reviewer assignments, and reviews.

The browser should not connect directly to MySQL. Flask is the controlled
middle layer:

1. The browser sends an HTTP request.
2. Flask validates the request and runs a parameterized SQL statement.
3. MySQL stores or returns the data.
4. Flask sends an HTML page or another HTTP response to the browser.

## 2. Tables, rows, and columns

- A **table** is a collection of related records, similar to a spreadsheet.
- A **row** is one record in a table.
- A **column** is one attribute of each record.

For example, one row in `users` represents one ConferenceFlow user. Its
columns include `user_id`, `full_name`, `email`, `password`, and `role`.

The current schema is in [schema.sql](../schema.sql).

## 3. Current tables and relationships

### `users`

Stores account information:

- `user_id`: auto-incrementing primary key
- `full_name`: user's name
- `email`: unique email address
- `password`: password hash, not the original password
- `role`: `admin`, `reviewer`, or `author`
- `created_at`: creation timestamp

### `papers`

Stores paper information and its uploaded file path:

- `paper_id`: primary key
- `title`, `abstract`, and `keywords`
- `file_name` and `uploaded_file_path`
- `status`, defaulting to `Pending`
- `submitted_at`: submission timestamp

The current table does **not** contain an author or submission-owner foreign
key. This is an important design gap because the application cannot reliably
connect a paper to the user who submitted it.

### `review_assignments`

Represents the relationship between papers and reviewers:

- `assignment_id`: primary key
- `paper_id`: foreign key to `papers.paper_id`
- `reviewer_id`: foreign key to `users.user_id`
- `assigned_at`: assignment timestamp

This is an explicit join table. It is needed because one paper can have
multiple reviewers and one reviewer can receive multiple papers. That is a
many-to-many relationship.

### `reviews`

Stores a review for an assignment:

- `review_id`: primary key
- `assignment_id`: foreign key to `review_assignments.assignment_id`
- four component scores
- `overall_score`
- `recommendation`
- `review_comment`
- `reviewed_at`

The current foreign key means a review refers to a valid assignment. It does
not yet prevent multiple reviews for the same assignment.

## 4. Keys and relationships

A **primary key** uniquely identifies a row. For example,
`users.user_id = 7` identifies one user.

A **foreign key** stores a value that must refer to a related row. For
example, `review_assignments.paper_id` must refer to an existing paper.
Foreign keys protect referential integrity: they prevent an assignment from
pointing at a paper that does not exist.

Common relationship types:

- **One-to-one**: one row relates to at most one row in another table.
- **One-to-many**: one user could own many papers.
- **Many-to-many**: many reviewers can review many papers. The
  `review_assignments` table represents this relationship explicitly.

The current relationships are:

```text
users 1 ---- many review_assignments many ---- 1 papers
review_assignments 1 ---- many reviews
```

The proposed future relationship is:

```text
users 1 ---- many papers
```

by adding a paper-owner foreign key after approval.

## 5. SQL operations in the current application

### `SELECT`

`SELECT` reads rows. The login route uses a parameterized query:

```python
cur.execute("""
    SELECT * FROM users
    WHERE email=%s
""", (email,))
```

The `%s` placeholder is supplied separately from the SQL string. The
connector safely sends the value as data rather than treating it as SQL code.

### `INSERT`

Registration inserts a new user:

```python
cur.execute("""
    INSERT INTO users (full_name, email, password, role)
    VALUES (%s, %s, %s, %s)
""", (full_name, email, hashed_password, role))
```

### `UPDATE`

Reviewer assignment updates a paper status:

```python
cur.execute("""
    UPDATE papers
    SET status = 'Under Review'
    WHERE paper_id = %s
""", (paper_id,))
```

### `DELETE`

The current Flask routes do not execute a `DELETE` statement. A future delete
operation should be authorization-protected and should use a parameterized
condition. It should also define what happens to related assignments and
reviews before it is implemented.

## 6. `WHERE`, `ORDER BY`, and `JOIN`

- `WHERE` filters rows, such as users with `role='reviewer'`.
- `ORDER BY` sorts rows, such as papers by newest `submitted_at`.
- `JOIN` combines related tables so one query can return related information.

The current code mostly queries one table at a time. A future reviewer
dashboard could use a join similar to:

```sql
SELECT p.title, ra.assignment_id
FROM review_assignments AS ra
JOIN papers AS p ON p.paper_id = ra.paper_id
WHERE ra.reviewer_id = %s
ORDER BY ra.assigned_at DESC;
```

The reviewer ID must still be passed as a parameter, not concatenated into
the SQL string.

## 7. Normalization and duplicate data

Normalization means storing each fact in an appropriate place and linking
related facts with keys. For example, reviewer contact information belongs in
`users`, not in every assignment row.

Duplicating a reviewer's email in every assignment would create update
problems: changing the email would require changing many rows, and some rows
could become inconsistent.

The current design separates users, papers, assignments, and reviews, which
is a good normalized starting point. However, the missing paper-owner link
means an important relationship is not represented yet.

## 8. Indexes

An index is an additional data structure that helps MySQL find rows without
scanning an entire table.

The current schema has indexes from primary keys and a unique index for
`users.email`. MySQL also creates or requires indexes for foreign-key
relationships.

Useful future indexes may include:

- `papers.submitted_at` for newest-paper queries;
- `papers.status` for status dashboards;
- a composite unique index on `(paper_id, reviewer_id)` to prevent duplicate
  assignments;
- a unique index on `reviews.assignment_id` if one assignment may have only
  one review.

Indexes improve reads but use storage and can make writes slightly more
expensive. They should support real query patterns rather than be added
without a reason.

## 9. Transactions, commit, and rollback

A transaction groups related database changes.

The assignment route performs two related writes:

1. insert a row into `review_assignments`;
2. update the paper status.

It calls `conn.commit()` after both statements. This is correct in principle:
both changes should become permanent together.

If an error occurs after the first statement but before the commit, the
connection should call `rollback()` before it is closed. Otherwise a future
database operation could be affected by an unfinished transaction, depending
on the connector state.

The current routes close connections on their normal paths but do not use
`try`/`except`/`finally` blocks for every database operation. A future
database-access cleanup should guarantee rollback on failure and closure of
both cursors and connections.

## 10. Connection versus cursor

A **connection** represents the session between Python and MySQL. It owns
transaction state and provides `commit()` and `rollback()`.

A **cursor** sends SQL through a connection and reads results:

```python
conn = get_connection()
cur = conn.cursor(dictionary=True)
cur.execute("SELECT ...")
rows = cur.fetchall()
```

`dictionary=True` makes each result row accessible by column name, such as
`user["password"]`, instead of only by numeric position.

The helper in [db.py](../db.py) creates a new connection using environment
variables. Importing the helper does not connect to MySQL; a connection is
opened only when `get_connection()` is called.

## 11. Current database-access safety review

Already implemented:

- credentials are read from environment variables;
- SQL values from forms use parameterized placeholders;
- password values are hashed before insertion;
- normal successful database paths close their connections;
- the assignment operation commits its related writes together.

Implemented in Phase 2:

- `db.connection_scope()` closes connections and rolls back when scoped work
  raises an exception;
- `db.cursor_scope()` closes cursors as well as their connections;
- database-backed routes use these scopes;
- failed database operations are logged using exception type only and shown to
  users as generic messages;
- the assignment operation commits its related writes together.

Still needs improvement:

- paper ownership is not represented;
- duplicate assignments and duplicate reviews are not protected by database
  constraints;
- most business-critical columns are nullable because the schema does not
  specify `NOT NULL`;
- the public registration form currently permits the `admin` role, which is
  an authorization issue outside the schema itself.

## 12. Proposed schema changes (not applied)

These changes should be reviewed before any migration:

1. Add `author_id` to `papers` as a foreign key to `users.user_id`.
   This records ownership and enables author-specific queries.
2. Add `NOT NULL` to required fields after checking existing data for nulls.
3. Add a unique constraint on `review_assignments(paper_id, reviewer_id)`.
4. Add a unique constraint on `reviews(assignment_id)` if the business rule
   is one review per assignment.
5. Add targeted indexes for the actual dashboard queries.
6. Consider replacing free-form paper statuses with a controlled design
   after confirming the allowed workflow states.

These changes may fail on an existing database if current data violates the
new rules. They must not be applied to production automatically. Before
creating a migration, inspect the target database and decide how existing
rows should be repaired.

## 13. Interview questions and answers

### 1. Why is `review_assignments` a separate table?

Because papers and reviewers have a many-to-many relationship. A separate
table stores each paper-reviewer pair and can also store relationship data,
such as `assigned_at`.

### 2. How does parameterized SQL reduce injection risk?

The SQL structure and user-provided values are sent separately. A value such
as an email is treated as data, not executable SQL syntax.

### 3. What does a foreign key protect?

It protects referential integrity. For example, an assignment cannot refer to
a paper ID that does not exist.

### 4. Why is `commit()` important?

SQL writes are part of a transaction. `commit()` makes successful changes
permanent. Without it, an insert or update may not be saved.

### 5. Why should a failed transaction call `rollback()`?

Rollback clears the incomplete transaction so partial work is not retained
and the connection can safely be reused or closed.

## Short quiz

1. Which table currently connects a paper to a reviewer?
2. Why is `users.email` different from an ordinary `VARCHAR` column?
3. What is the difference between a connection and a cursor?
4. Which SQL clause filters rows?
5. What schema field is currently missing to identify a paper's author?

Answers:

1. `review_assignments`.
2. It has a unique constraint.
3. A connection represents the MySQL session and transaction; a cursor
   executes SQL and reads results through that connection.
4. `WHERE`.
5. An author or submission-owner foreign key such as `author_id`.
