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

    title VARCHAR(255),

    abstract TEXT,

    keywords TEXT,

    file_name VARCHAR(255),

    uploaded_file_path TEXT,

    status VARCHAR(50) DEFAULT 'Pending',

    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

);



CREATE TABLE review_assignments (

    assignment_id INT PRIMARY KEY AUTO_INCREMENT,

    paper_id INT,

    reviewer_id INT,

    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (paper_id)
    REFERENCES papers(paper_id),

    FOREIGN KEY (reviewer_id)
    REFERENCES users(user_id)

);



CREATE TABLE reviews (

    review_id INT PRIMARY KEY AUTO_INCREMENT,

    assignment_id INT,

    technical_merit FLOAT,

    readability FLOAT,

    originality FLOAT,

    relevance FLOAT,

    overall_score FLOAT,

    recommendation VARCHAR(50),

    review_comment TEXT,

    reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (assignment_id)
    REFERENCES review_assignments(assignment_id)

);