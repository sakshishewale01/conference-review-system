CREATE DATABASE conf_review_system;

USE conf_review_system;



CREATE TABLE users (

    user_id INT PRIMARY KEY AUTO_INCREMENT,

    full_name VARCHAR(150),

    email VARCHAR(150) UNIQUE,

    password TEXT,

    role ENUM('admin','reviewer','author'),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

);



CREATE TABLE papers (

    paper_id INT PRIMARY KEY AUTO_INCREMENT,

    author_id INT,

    title VARCHAR(255),

    abstract TEXT,

    keywords TEXT,

    file_name VARCHAR(255),

    uploaded_file_path TEXT,

    status VARCHAR(50) DEFAULT 'Pending',

    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    decision_notes TEXT,

    decided_by INT,

    decided_at TIMESTAMP NULL,

    decision_released_at TIMESTAMP NULL,

    FOREIGN KEY (author_id) REFERENCES users(user_id),

    FOREIGN KEY (decided_by) REFERENCES users(user_id)

);


CREATE TABLE notifications (

    notification_id INT PRIMARY KEY AUTO_INCREMENT,

    recipient_id INT NOT NULL,

    title VARCHAR(150) NOT NULL,

    message VARCHAR(500) NOT NULL,

    link VARCHAR(500),

    event_key VARCHAR(255) NOT NULL UNIQUE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    read_at TIMESTAMP NULL,

    FOREIGN KEY (recipient_id) REFERENCES users(user_id),

    INDEX idx_notifications_recipient_read (recipient_id, read_at)

);



CREATE TABLE review_assignments (

    assignment_id INT PRIMARY KEY AUTO_INCREMENT,

    paper_id INT NOT NULL,

    reviewer_id INT NOT NULL,

    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (paper_id)
    REFERENCES papers(paper_id),

    FOREIGN KEY (reviewer_id)
    REFERENCES users(user_id),

    UNIQUE (paper_id, reviewer_id)

);



CREATE TABLE reviews (

    review_id INT PRIMARY KEY AUTO_INCREMENT,

    assignment_id INT NOT NULL,

    technical_merit FLOAT,

    readability FLOAT,

    originality FLOAT,

    relevance FLOAT,

    overall_score FLOAT,

    recommendation VARCHAR(50),

    review_comment TEXT,

    reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (assignment_id)
    REFERENCES review_assignments(assignment_id),

    UNIQUE (assignment_id)

);