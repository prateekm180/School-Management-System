-- ===============================================================================
-- SCHOOL MANAGEMENT SYSTEM - DATABASE BACKUP SCRIPT
-- Target Database: school_management
-- Generated for Class 12th Board Project Execution
-- ===============================================================================

CREATE DATABASE IF NOT EXISTS school_management;
USE school_management;

-- Disable foreign key checks temporarily to drop existing tables cleanly
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS library_transactions;
DROP TABLE IF EXISTS library_books;
DROP TABLE IF EXISTS fee_payments;
DROP TABLE IF EXISTS account_heads;
DROP TABLE IF EXISTS student_marks;
DROP TABLE IF EXISTS exam_papers;
DROP TABLE IF EXISTS attendance_records;
DROP TABLE IF EXISTS teacher_mappings;
DROP TABLE IF EXISTS employees;
DROP TABLE IF EXISTS student_promotion_history;
DROP TABLE IF EXISTS student_admission_queue;
DROP TABLE IF EXISTS students;
DROP TABLE IF EXISTS user_sessions;
DROP TABLE IF EXISTS users;
SET FOREIGN_KEY_CHECKS = 1;

-- -------------------------------------------------------------------------------
-- 1. AUTHENTICATION & ACCESS CONTROL SYSTEMS
-- -------------------------------------------------------------------------------

CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(64) NOT NULL, -- Storing SHA-256 Hashes securely
    salt VARCHAR(32) NOT NULL,
    role ENUM('Admin', 'Principal', 'Teacher', 'Accountant', 'Clerk') NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE,
    status ENUM('Active', 'Suspended') DEFAULT 'Active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Default sample users (Password for all accounts is: Password@123)
-- Real setups generate salts randomly; these are hardcoded for immediate demo capability
INSERT INTO users (username, password_hash, salt, role, full_name, email) VALUES
('admin01', 'e137f2628469c450c226462744d03da0a184ef15df2dfb421a1f0a424b94cbf1', 'salt12345', 'Admin', 'Aditya Sharma', 'admin@school.edu'),
('teacher_amit', '44bd83344b1c7db1a153202e86a51d95c1c874df1cfdb12f6a8e8f8ec31a31d9', 'salt56789', 'Teacher', 'Amit Verma', 'amit.verma@school.edu'),
('finance_head', '83c0f49673dfa10f9bd3e061ad186526fc8e03a11a8b7dd55a153a8ffb246a4e', 'salt99999', 'Accountant', 'Rohan Das', 'rohan.das@school.edu');

-- -------------------------------------------------------------------------------
-- 2. STUDENT INFORMATION & PROMOTION MODULES
-- -------------------------------------------------------------------------------

CREATE TABLE students (
    student_id INT AUTO_INCREMENT PRIMARY KEY,
    admission_no VARCHAR(20) UNIQUE NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    date_of_birth DATE NOT NULL,
    gender ENUM('Male', 'Female', 'Other') NOT NULL,
    current_class VARCHAR(10) NOT NULL,     -- e.g., '12-A', '11-B'
    guardian_name VARCHAR(100) NOT NULL,
    guardian_phone VARCHAR(15) NOT NULL,
    guardian_email VARCHAR(100),
    residential_address TEXT,
    admission_date DATE NOT NULL,
    status ENUM('Active', 'Passed Out', 'Transferred', 'Suspended') DEFAULT 'Active'
) ENGINE=InnoDB;

INSERT INTO students (admission_no, first_name, last_name, date_of_birth, gender, current_class, guardian_name, guardian_phone, guardian_email, residential_address, admission_date) VALUES
('ADM2024001', 'Aarav', 'Mehta', '2008-05-14', 'Male', '12-A', 'Sanjay Mehta', '9876543210', 'sanjay@gmail.com', 'Flat 402, Green Avenue, Delhi', '2024-04-05'),
('ADM2024002', 'Diya', 'Nair', '2008-11-22', 'Female', '12-A', 'Ramesh Nair', '9812345678', 'ramesh@nair.com', 'House 12, Sector 4, Gurgaon', '2024-04-06'),
('ADM2025089', 'Kabir', 'Singh', '2009-02-10', 'Male', '11-B', 'Harpreet Singh', '9988776655', 'harpreet@singh.com', 'MIG Flats, Rajouri Garden', '2025-04-02');

CREATE TABLE student_admission_queue (
    request_id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    applied_class VARCHAR(10) NOT NULL,
    guardian_name VARCHAR(100) NOT NULL,
    guardian_phone VARCHAR(15) NOT NULL,
    previous_school_details TEXT,
    submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    review_status ENUM('Pending', 'Approved', 'Rejected') DEFAULT 'Pending',
    remarks TEXT
) ENGINE=InnoDB;

INSERT INTO student_admission_queue (first_name, last_name, applied_class, guardian_name, guardian_phone, previous_school_details) VALUES
('Ananya', 'Sen', '11-A', 'Joydeep Sen', '9432109876', 'St. Xaviers High School, Marks: 92%'),
('Rohan', 'Joshi', '12-B', 'Alok Joshi', '9560123456', 'Delhi Public School, Family relocating');

CREATE TABLE student_promotion_history (
    history_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    from_class VARCHAR(10) NOT NULL,
    to_class VARCHAR(10) NOT NULL,
    academic_year VARCHAR(9) NOT NULL, -- e.g., '2025-2026'
    promotion_date DATE NOT NULL,
    status_result ENUM('Passed', 'Detained') NOT NULL,
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- -------------------------------------------------------------------------------
-- 3. EMPLOYEE & FACULTY MANAGEMENT
-- -------------------------------------------------------------------------------

CREATE TABLE employees (
    employee_id INT AUTO_INCREMENT PRIMARY KEY,
    employee_code VARCHAR(20) UNIQUE NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    designation VARCHAR(50) NOT NULL,  -- e.g., 'PGT Computer Science', 'Accountant'
    department ENUM('Academic', 'Administration', 'Finance', 'Support') NOT NULL,
    phone_number VARCHAR(15) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    joining_date DATE NOT NULL,
    monthly_salary DECIMAL(10,2) NOT NULL,
    status ENUM('Active', 'Resigned', 'Terminated') DEFAULT 'Active'
) ENGINE=InnoDB;

INSERT INTO employees (employee_code, first_name, last_name, designation, department, phone_number, email, joining_date, monthly_salary) VALUES
('EMP101', 'Amit', 'Verma', 'PGT Mathematics', 'Academic', '9898989898', 'amit.verma@school.edu', '2018-07-15', 65000.00),
('EMP102', 'Sunita', 'Rao', 'PGT Computer Science', 'Academic', '9797979797', 'sunita.rao@school.edu', '2020-01-10', 68000.00),
('EMP201', 'Rohan', 'Das', 'Senior Accountant', 'Finance', '9696969696', 'rohan.das@school.edu', '2019-03-22', 45000.00);

CREATE TABLE teacher_mappings (
    mapping_id INT AUTO_INCREMENT PRIMARY KEY,
    teacher_id INT NOT NULL,
    class_assigned VARCHAR(10) NOT NULL,
    subject_assigned VARCHAR(50) NOT NULL,
    FOREIGN KEY (teacher_id) REFERENCES employees(employee_id) ON DELETE CASCADE
) ENGINE=InnoDB;

INSERT INTO teacher_mappings (teacher_id, class_assigned, subject_assigned) VALUES
(1, '12-A', 'Mathematics'),
(2, '12-A', 'Computer Science'),
(2, '11-B', 'Computer Science');

-- -------------------------------------------------------------------------------
-- 4. ATTENDANCE SYSTEM MODULE
-- -------------------------------------------------------------------------------

CREATE TABLE attendance_records (
    attendance_id INT AUTO_INCREMENT PRIMARY KEY,
    entity_type ENUM('Student', 'Employee') NOT NULL,
    entity_id INT NOT NULL, -- maps to student_id or employee_id based on type
    date DATE NOT NULL,
    status ENUM('Present', 'Absent', 'Leave') NOT NULL,
    remarks VARCHAR(255),
    UNIQUE KEY unique_daily_attendance (entity_type, entity_id, date)
) ENGINE=InnoDB;

INSERT INTO attendance_records (entity_type, entity_id, date, status, remarks) VALUES
('Student', 1, '2026-07-06', 'Present', 'Arrived on time'),
('Student', 2, '2026-07-06', 'Absent', 'Uninformed'),
('Employee', 1, '2026-07-06', 'Present', 'Routine check'),
('Employee', 2, '2026-07-06', 'Leave', 'Medical application approved');

-- -------------------------------------------------------------------------------
-- 5. EXAMINATIONS & ACADEMIC GRADING ENGINE
-- -------------------------------------------------------------------------------

CREATE TABLE exam_papers (
    paper_id INT AUTO_INCREMENT PRIMARY KEY,
    exam_name VARCHAR(50) NOT NULL,      -- e.g., 'First Term', 'Pre-Board'
    class_name VARCHAR(10) NOT NULL,
    subject_name VARCHAR(50) NOT NULL,
    max_marks INT NOT NULL DEFAULT 100,
    pass_marks INT NOT NULL DEFAULT 33,
    exam_date DATE NOT NULL
) ENGINE=InnoDB;

INSERT INTO exam_papers (exam_name, class_name, subject_name, max_marks, pass_marks, exam_date) VALUES
('First Term', '12-A', 'Mathematics', 100, 33, '2026-09-15'),
('First Term', '12-A', 'Computer Science', 70, 23, '2026-09-18');

CREATE TABLE student_marks (
    marks_id INT AUTO_INCREMENT PRIMARY KEY,
    paper_id INT NOT NULL,
    student_id INT NOT NULL,
    marks_obtained DECIMAL(5,2) NOT NULL,
    is_absent BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (paper_id) REFERENCES exam_papers(paper_id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    UNIQUE KEY unique_student_paper (paper_id, student_id)
) ENGINE=InnoDB;

INSERT INTO student_marks (paper_id, student_id, marks_obtained, is_absent) VALUES
(1, 1, 88.50, FALSE),
(1, 2, 92.00, FALSE),
(2, 1, 65.00, FALSE);

-- -------------------------------------------------------------------------------
-- 6. FINANCIAL LEDGERS & FEE MANAGERS
-- -------------------------------------------------------------------------------

CREATE TABLE account_heads (
    head_id INT AUTO_INCREMENT PRIMARY KEY,
    head_name VARCHAR(100) UNIQUE NOT NULL, -- e.g., 'Tuition Fee', 'Lab Maintenance'
    type ENUM('Revenue', 'Expense') NOT NULL,
    description TEXT
) ENGINE=InnoDB;

INSERT INTO account_heads (head_name, type, description) VALUES
('Tuition Fee', 'Revenue', 'Quarterly core educational charges'),
('Computer Lab Fee', 'Revenue', 'Practical maintenance charges for systems'),
('Staff Salaries', 'Expense', 'Disbursements to academic and non-academic staff'),
('Electricity Bill', 'Expense', 'Monthly infrastructural utility operations cost');

CREATE TABLE fee_payments (
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    head_id INT NOT NULL,
    amount_due DECIMAL(10,2) NOT NULL,
    amount_paid DECIMAL(10,2) DEFAULT 0.00,
    due_date DATE NOT NULL,
    payment_date DATE,
    payment_mode ENUM('Cash', 'Cheque', 'Online', 'Pending') DEFAULT 'Pending',
    transaction_ref VARCHAR(50),
    status ENUM('Paid', 'Partial', 'Unpaid') DEFAULT 'Unpaid',
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (head_id) REFERENCES account_heads(head_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

INSERT INTO fee_payments (student_id, head_id, amount_due, amount_paid, due_date, payment_date, payment_mode, status) VALUES
(1, 1, 15000.00, 15000.00, '2026-04-15', '2026-04-10', 'Online', 'Paid'),
(1, 2, 25000.00, 10000.00, '2026-05-01', '2026-05-01', 'Cash', 'Partial'),
(2, 1, 15000.00, 0.00, '2026-04-15', NULL, 'Pending', 'Unpaid');

-- -------------------------------------------------------------------------------
-- 7. LIBRARY RESOURCE MANAGEMENT SYSTEM
-- -------------------------------------------------------------------------------

CREATE TABLE library_books (
    book_id INT AUTO_INCREMENT PRIMARY KEY,
    isbn VARCHAR(20) UNIQUE NOT NULL,
    title VARCHAR(150) NOT NULL,
    author VARCHAR(100) NOT NULL,
    publisher VARCHAR(100),
    edition VARCHAR(20),
    total_copies INT NOT NULL DEFAULT 1,
    available_copies INT NOT NULL DEFAULT 1,
    rack_location VARCHAR(20)                  -- e.g., 'Shelf C-3'
) ENGINE=InnoDB;

INSERT INTO library_books (isbn, title, author, total_copies, available_copies, rack_location) VALUES
('978-8177001', 'Core Python Programming', 'Dr. R. Nageswara Rao', 5, 4, 'Shelf P-1'),
('978-9352135', 'Concepts of Physics (Vol 1)', 'H.C. Verma', 10, 10, 'Shelf P-4'),
('978-0131103', 'The C Programming Language', 'Kernighan & Ritchie', 3, 2, 'Shelf C-2');

CREATE TABLE library_transactions (
    transaction_id INT AUTO_INCREMENT PRIMARY KEY,
    book_id INT NOT NULL,
    borrower_type ENUM('Student', 'Employee') NOT NULL,
    borrower_id INT NOT NULL,                  -- maps to student_id or employee_id
    issue_date DATE NOT NULL,
    due_date DATE NOT NULL,
    return_date DATE,
    fine_accrued DECIMAL(6,2) DEFAULT 0.00,
    status ENUM('Issued', 'Returned', 'Overdue') DEFAULT 'Issued',
    FOREIGN KEY (book_id) REFERENCES library_books(book_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

INSERT INTO library_transactions (book_id, borrower_type, borrower_id, issue_date, due_date, return_date, status) VALUES
(1, 'Student', 1, '2026-06-20', '2026-07-04', NULL, 'Overdue'), -- Outstanding Overdue
(3, 'Employee', 2, '2026-07-01', '2026-07-15', NULL, 'Issued');

-- -------------------------------------------------------------------------------
-- OPTIONAL OPTIMIZATION INDEXES
-- -------------------------------------------------------------------------------
CREATE INDEX idx_student_class ON students(current_class);
CREATE INDEX idx_attendance_lookup ON attendance_records(date, entity_type);
CREATE INDEX idx_fee_status ON fee_payments(status);

-- Complete