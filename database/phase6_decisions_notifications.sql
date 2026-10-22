-- ConferenceFlow Phase 6 migration proposal.
-- Inspect existing data and apply only to a local backup first.
-- These statements are intentionally not executed by the application.

-- ALTER TABLE papers
--     ADD COLUMN author_id INT NULL AFTER paper_id,
--     ADD COLUMN decision_notes TEXT NULL,
--     ADD COLUMN decided_by INT NULL,
--     ADD COLUMN decided_at TIMESTAMP NULL,
--     ADD COLUMN decision_released_at TIMESTAMP NULL,
--     ADD CONSTRAINT fk_papers_author
--         FOREIGN KEY (author_id) REFERENCES users(user_id),
--     ADD CONSTRAINT fk_papers_decided_by
--         FOREIGN KEY (decided_by) REFERENCES users(user_id);

-- Existing papers have no trustworthy owner in the original schema.
-- Review and manually approve an author_id backfill before adding ownership
-- enforcement for historical rows.

-- CREATE TABLE notifications (
--     notification_id INT PRIMARY KEY AUTO_INCREMENT,
--     recipient_id INT NOT NULL,
--     title VARCHAR(150) NOT NULL,
--     message VARCHAR(500) NOT NULL,
--     link VARCHAR(500) NULL,
--     event_key VARCHAR(255) NOT NULL UNIQUE,
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     read_at TIMESTAMP NULL,
--     FOREIGN KEY (recipient_id) REFERENCES users(user_id),
--     INDEX idx_notifications_recipient_read (recipient_id, read_at)
-- );

-- Rollback plan after approval and backup:
-- ALTER TABLE papers DROP FOREIGN KEY fk_papers_author;
-- ALTER TABLE papers DROP FOREIGN KEY fk_papers_decided_by;
-- ALTER TABLE papers DROP COLUMN author_id, DROP COLUMN decision_notes,
--     DROP COLUMN decided_by, DROP COLUMN decided_at,
--     DROP COLUMN decision_released_at;
-- DROP TABLE notifications;
