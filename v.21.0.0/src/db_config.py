"""
===============================================================================
 db_config.py
-------------------------------------------------------------------------------
 PURPOSE
    1. Central place that manages the MySQL connection for the whole project.
    2. On first run, it reads schema.sql and builds the entire database
       (all tables, keys, indexes) automatically -- nothing to do by hand.
    3. Seeds the database with realistic sample/mock data (roles, users,
       classes, subjects, a few students & employees, grading scale, etc.)
       so the project is demo-ready immediately after setup.

 USAGE
    Run this file directly ONCE to (re)initialize the database:
        python db_config.py

    Other modules (auth.py, student.py, finance.py, ...) will simply do:
        from db_config import get_connection
        conn = get_connection()

 REQUIREMENTS
    pip install mysql-connector-python

 NOTE ON PASSWORDS
    Real passwords must never be stored in plain text. We hash every seed
    password with SHA-256 + a per-user salt using the same helper functions
    that auth.py (Step 3) will use, so the login logic stays consistent.
===============================================================================
"""

import os
import sys
import hashlib
import secrets
import mysql.connector
from mysql.connector import Error

# -------------------------------------------------------------------------
# 1. CONNECTION SETTINGS
#    Edit these to match your local MySQL server. In a real deployment these
#    would come from environment variables, not hard-coded values.
# -------------------------------------------------------------------------
DB_CONFIG = {
    "host": os.environ.get("SMS_DB_HOST", "localhost"),
    "user": os.environ.get("SMS_DB_USER", "root"),
    "password": os.environ.get("SMS_DB_PASSWORD", "your_mysql_password"),
    "port": int(os.environ.get("SMS_DB_PORT", 3306)),
}

DB_NAME = "school_mgmt_system"
SCHEMA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")


# -------------------------------------------------------------------------
# 2. CONNECTION HELPERS
# -------------------------------------------------------------------------
def get_server_connection():
    """Connect to the MySQL SERVER (no database selected yet). Used only
    during initialization, since the target database may not exist yet."""
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Error as e:
        print(f"[FATAL] Could not connect to MySQL server: {e}")
        sys.exit(1)


def get_connection():
    """Connect directly to the school_mgmt_system database.
    This is the function every other module (auth.py, student.py, ...)
    should import and call."""
    try:
        return mysql.connector.connect(database=DB_NAME, **DB_CONFIG)
    except Error as e:
        print(f"[FATAL] Could not connect to database '{DB_NAME}': {e}")
        sys.exit(1)


# -------------------------------------------------------------------------
# 3. PASSWORD HASHING HELPERS (shared contract with auth.py in Step 3)
# -------------------------------------------------------------------------
def hash_password(plain_password: str, salt: str = None) -> tuple:
    """Returns (password_hash, salt). Uses SHA-256(salt + password).
    A random salt is generated if one isn't supplied."""
    if salt is None:
        salt = secrets.token_hex(16)
    digest = hashlib.sha256((salt + plain_password).encode("utf-8")).hexdigest()
    return digest, salt


# -------------------------------------------------------------------------
# 4. SCHEMA LOADER
#    Reads schema.sql and executes it as a multi-statement script.
# -------------------------------------------------------------------------
def build_schema():
    if not os.path.exists(SCHEMA_FILE):
        print(f"[FATAL] schema.sql not found at {SCHEMA_FILE}")
        sys.exit(1)

    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        sql_script = f.read()

    conn = get_server_connection()
    cursor = conn.cursor()
    try:
        # multi=True lets us run the entire .sql file (many ';'-separated
        # statements) in one go instead of splitting it manually.
        for result in cursor.execute(sql_script, multi=True):
            pass
        conn.commit()
        print("[OK] Database schema created successfully from schema.sql")
    except Error as e:
        print(f"[FATAL] Error while building schema: {e}")
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()


# -------------------------------------------------------------------------
# 5. SEED DATA
#    Realistic starter data so every module has something to display.
# -------------------------------------------------------------------------
def seed_data():
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # ---- Institute profile -------------------------------------------------
        cursor.execute("""
            INSERT INTO institute_profile
                (institute_name, address_line, city, state, pincode, phone, email, website_url, established_year)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, ("Delhi Public Sr. Sec. School", "Sector 12, Rohini", "New Delhi", "Delhi",
              "110085", "011-27045678", "info@dpsdemo.edu.in", "www.dpsdemo.edu.in", 1985))

        # ---- Academic year -------------------------------------------------
        cursor.execute("""
            INSERT INTO academic_years (year_label, start_date, end_date, is_current)
            VALUES ('2025-2026', '2025-04-01', '2026-03-31', TRUE)
        """)
        academic_year_id = cursor.lastrowid

        # ---- Academic calendar sample events -------------------------------
        calendar_events = [
            (academic_year_id, "2025-08-15", "Independence Day", "HOLIDAY", "National holiday"),
            (academic_year_id, "2025-10-02", "Gandhi Jayanti", "HOLIDAY", "National holiday"),
            (academic_year_id, "2025-09-15", "Half Yearly Exams Begin", "EXAM", "Classes 9-12"),
            (academic_year_id, "2025-12-25", "Christmas / Winter Break", "HOLIDAY", "Winter vacation starts"),
            (academic_year_id, "2026-01-26", "Republic Day", "HOLIDAY", "National holiday"),
        ]
        cursor.executemany("""
            INSERT INTO academic_calendar (academic_year_id, event_date, title, event_type, description)
            VALUES (%s,%s,%s,%s,%s)
        """, calendar_events)

        # ---- Classes & Sections --------------------------------------------
        class_names = [(f"Class {i}", i) for i in range(1, 13)]
        cursor.executemany("INSERT INTO classes (class_name, class_order) VALUES (%s,%s)", class_names)

        cursor.execute("SELECT class_id FROM classes ORDER BY class_order")
        class_ids = [row[0] for row in cursor.fetchall()]

        sections_data = []
        for cid in class_ids:
            for sec in ("A", "B"):
                sections_data.append((cid, sec, "Room-" + str(cid) + sec, 40))
        cursor.executemany("""
            INSERT INTO sections (class_id, section_name, room_no, capacity) VALUES (%s,%s,%s,%s)
        """, sections_data)

        # ---- Subjects --------------------------------------------------------
        subjects = [
            ("English", "ENG", "THEORY", 100),
            ("Hindi", "HIN", "THEORY", 100),
            ("Mathematics", "MATH", "THEORY", 100),
            ("Science", "SCI", "BOTH", 100),
            ("Social Science", "SST", "THEORY", 100),
            ("Computer Science", "CS", "BOTH", 100),
            ("Physical Education", "PE", "PRACTICAL", 50),
        ]
        cursor.executemany("""
            INSERT INTO subjects (subject_name, subject_code, subject_type, max_marks_default)
            VALUES (%s,%s,%s,%s)
        """, subjects)

        cursor.execute("SELECT subject_id FROM subjects")
        subject_ids = [row[0] for row in cursor.fetchall()]

        class_subject_rows = [(cid, sid, False) for cid in class_ids for sid in subject_ids]
        cursor.executemany("""
            INSERT INTO class_subjects (class_id, subject_id, is_optional) VALUES (%s,%s,%s)
        """, class_subject_rows)

        # ---- Roles -------------------------------------------------------------
        roles = [
            ("ADMIN", "Full system access"),
            ("TEACHER", "Teaching staff - attendance, marks, own classes"),
            ("STUDENT", "Student self-service portal"),
            ("PARENT", "Parent/guardian view of a linked student"),
            ("ACCOUNTANT", "Finance & fee module access"),
            ("LIBRARIAN", "Library module access"),
        ]
        cursor.executemany("INSERT INTO roles (role_name, description) VALUES (%s,%s)", roles)

        cursor.execute("SELECT role_id, role_name FROM roles")
        role_map = {name: rid for rid, name in cursor.fetchall()}

        # ---- Permissions (sample ACL grid keys across modules) -----------------
        permissions = [
            ("STUDENT_ADD", "STUDENT", "Add a new student"),
            ("STUDENT_EDIT", "STUDENT", "Edit student details"),
            ("STUDENT_PROMOTE", "STUDENT", "Promote/detain students"),
            ("ATTENDANCE_MARK", "ATTENDANCE", "Mark daily attendance"),
            ("EXAM_MARKS_ENTRY", "EXAM", "Enter marks for an exam"),
            ("EXAM_REPORTCARD_VIEW", "EXAM", "View/generate report cards"),
            ("FEE_COLLECT", "FINANCE", "Collect student fees"),
            ("FEE_INVOICE_GENERATE", "FINANCE", "Generate fee invoices"),
            ("LIBRARY_ISSUE_RETURN", "LIBRARY", "Issue/return library books"),
            ("PAYROLL_PROCESS", "PAYROLL", "Process employee salary"),
            ("USER_MANAGE", "ADMIN", "Create/manage users & roles"),
            ("WEBSITE_MANAGE", "WEBSITE", "Manage news/gallery/events/notices"),
        ]
        cursor.executemany("""
            INSERT INTO permissions (permission_key, module_name, description) VALUES (%s,%s,%s)
        """, permissions)

        cursor.execute("SELECT permission_id, permission_key FROM permissions")
        perm_rows = cursor.fetchall()
        perm_map = {key: pid for pid, key in perm_rows}

        # ADMIN gets every permission; TEACHER/ACCOUNTANT/LIBRARIAN get relevant subsets
        role_perm_pairs = []
        for pid in perm_map.values():
            role_perm_pairs.append((role_map["ADMIN"], pid))

        teacher_perms = ["ATTENDANCE_MARK", "EXAM_MARKS_ENTRY", "EXAM_REPORTCARD_VIEW"]
        for key in teacher_perms:
            role_perm_pairs.append((role_map["TEACHER"], perm_map[key]))

        accountant_perms = ["FEE_COLLECT", "FEE_INVOICE_GENERATE", "PAYROLL_PROCESS"]
        for key in accountant_perms:
            role_perm_pairs.append((role_map["ACCOUNTANT"], perm_map[key]))

        role_perm_pairs.append((role_map["LIBRARIAN"], perm_map["LIBRARY_ISSUE_RETURN"]))

        cursor.executemany("""
            INSERT IGNORE INTO role_permissions (role_id, permission_id) VALUES (%s,%s)
        """, role_perm_pairs)

        # ---- Designations & Departments -----------------------------------
        designations = ["Principal", "Vice Principal", "PGT", "TGT", "Librarian",
                         "Accountant", "Clerk", "Peon"]
        cursor.executemany("INSERT INTO designations (title) VALUES (%s)", [(d,) for d in designations])

        departments = ["Administration", "Science", "Commerce", "Humanities", "Sports", "Library"]
        cursor.executemany("INSERT INTO departments (department_name) VALUES (%s)", [(d,) for d in departments])

        cursor.execute("SELECT designation_id, title FROM designations")
        designation_map = {title: did for did, title in cursor.fetchall()}
        cursor.execute("SELECT department_id, department_name FROM departments")
        department_map = {name: did for did, name in cursor.fetchall()}

        # ---- Sample Employees -----------------------------------------------
        employees = [
            ("EMP001", "Anita", "Sharma", "1978-05-14", "FEMALE",
             designation_map["Principal"], department_map["Administration"], "ADMIN",
             "9811100011", "anita.sharma@dpsdemo.edu.in", "2010-06-01"),
            ("EMP002", "Rajesh", "Kumar", "1985-02-20", "MALE",
             designation_map["PGT"], department_map["Science"], "TEACHING",
             "9811100022", "rajesh.kumar@dpsdemo.edu.in", "2015-07-10"),
            ("EMP003", "Sunita", "Verma", "1988-11-02", "FEMALE",
             designation_map["TGT"], department_map["Humanities"], "TEACHING",
             "9811100033", "sunita.verma@dpsdemo.edu.in", "2018-04-15"),
            ("EMP004", "Mohit", "Gupta", "1990-09-09", "MALE",
             designation_map["Accountant"], department_map["Administration"], "ADMIN",
             "9811100044", "mohit.gupta@dpsdemo.edu.in", "2019-01-20"),
            ("EMP005", "Kiran", "Devi", "1982-03-03", "FEMALE",
             designation_map["Librarian"], department_map["Library"], "SUPPORT",
             "9811100055", "kiran.devi@dpsdemo.edu.in", "2012-08-01"),
        ]
        cursor.executemany("""
            INSERT INTO employees
              (employee_code, first_name, last_name, dob, gender, designation_id,
               department_id, employee_type, phone, email, date_of_joining)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, employees)

        cursor.execute("SELECT employee_id, employee_code FROM employees")
        emp_map = {code: eid for eid, code in cursor.fetchall()}

        # Teacher <-> Subject <-> Class mapping (Rajesh: Science on Class 9-A, Sunita: English Class 9-A)
        cursor.execute("SELECT class_id FROM classes WHERE class_name='Class 9'")
        class9_id = cursor.fetchone()[0]
        cursor.execute("SELECT section_id FROM sections WHERE class_id=%s AND section_name='A'", (class9_id,))
        section9a_id = cursor.fetchone()[0]
        cursor.execute("SELECT subject_id FROM subjects WHERE subject_code='SCI'")
        sci_id = cursor.fetchone()[0]
        cursor.execute("SELECT subject_id FROM subjects WHERE subject_code='ENG'")
        eng_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO teacher_subject_mapping
                (employee_id, class_id, section_id, subject_id, academic_year_id, is_class_teacher)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (emp_map["EMP002"], class9_id, section9a_id, sci_id, academic_year_id, True))

        cursor.execute("""
            INSERT INTO teacher_subject_mapping
                (employee_id, class_id, section_id, subject_id, academic_year_id, is_class_teacher)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (emp_map["EMP003"], class9_id, section9a_id, eng_id, academic_year_id, False))

        # ---- Sample Students --------------------------------------------------
        students = [
            ("ADM2025001", "Aarav", "Mehta", "2010-06-15", "MALE", "O+", "General",
             "New Delhi Sec-12", "9899911111", "aarav.parent@example.com",
             "Vikram Mehta", "Pooja Mehta", class9_id, section9a_id, academic_year_id,
             1, "2025-04-01", "REGULAR"),
            ("ADM2025002", "Diya", "Singh", "2010-08-22", "FEMALE", "B+", "General",
             "New Delhi Sec-14", "9899922222", "diya.parent@example.com",
             "Rohit Singh", "Neha Singh", class9_id, section9a_id, academic_year_id,
             2, "2025-04-01", "REGULAR"),
            ("ADM2025003", "Kabir", "Khan", "2010-01-10", "MALE", "A+", "OBC",
             "New Delhi Sec-9", "9899933333", "kabir.parent@example.com",
             "Imran Khan", "Sara Khan", class9_id, section9a_id, academic_year_id,
             3, "2025-04-02", "ONLINE"),
        ]
        cursor.executemany("""
            INSERT INTO students
              (admission_no, first_name, last_name, dob, gender, blood_group, category,
               address, phone, email, father_name, mother_name, class_id, section_id,
               academic_year_id, roll_no, admission_date, admission_mode)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, students)

        cursor.execute("SELECT student_id, admission_no FROM students")
        student_map = {adm: sid for sid, adm in cursor.fetchall()}

        # ---- Users (login accounts) linked to roles/employees/students --------
        seed_users = [
            ("admin", "Admin@123", "ADMIN", "System Administrator", "admin@dpsdemo.edu.in", None, None),
            ("rajesh.kumar", "Teach@123", "TEACHER", "Rajesh Kumar", "rajesh.kumar@dpsdemo.edu.in",
             None, emp_map["EMP002"]),
            ("mohit.gupta", "Acct@123", "ACCOUNTANT", "Mohit Gupta", "mohit.gupta@dpsdemo.edu.in",
             None, emp_map["EMP004"]),
            ("kiran.devi", "Lib@123", "LIBRARIAN", "Kiran Devi", "kiran.devi@dpsdemo.edu.in",
             None, emp_map["EMP005"]),
            ("aarav.mehta", "Stud@123", "STUDENT", "Aarav Mehta", "aarav.parent@example.com",
             student_map["ADM2025001"], None),
        ]

        for username, plain_pw, role_name, full_name, email, stud_id, emp_id in seed_users:
            pw_hash, salt = hash_password(plain_pw)
            cursor.execute("""
                INSERT INTO users
                    (username, password_hash, salt, role_id, full_name, email,
                     linked_student_id, linked_employee_id, is_active)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,TRUE)
            """, (username, pw_hash, salt, role_map[role_name], full_name, email, stud_id, emp_id))

        # ---- Grading scale (CBSE-style 9-point grade bands) --------------------
        grading_scale = [
            ("A1", 91, 100, 10.0, "Outstanding"),
            ("A2", 81, 90.99, 9.0, "Excellent"),
            ("B1", 71, 80.99, 8.0, "Very Good"),
            ("B2", 61, 70.99, 7.0, "Good"),
            ("C1", 51, 60.99, 6.0, "Fair"),
            ("C2", 41, 50.99, 5.0, "Average"),
            ("D",  33, 40.99, 4.0, "Below Average"),
            ("E",  0,  32.99, 0.0, "Needs Improvement / Fail"),
        ]
        cursor.executemany("""
            INSERT INTO grading_scale (grade_label, min_percent, max_percent, grade_point, remark)
            VALUES (%s,%s,%s,%s,%s)
        """, grading_scale)

        # ---- Account heads (Finance) --------------------------------------
        account_heads = [
            ("Tuition Fee", "INCOME"), ("Transport Fee", "INCOME"),
            ("Admission Fee", "INCOME"), ("Library Fine", "INCOME"),
            ("Salary Expense", "EXPENSE"), ("Electricity Bill", "EXPENSE"),
            ("Stationery", "EXPENSE"), ("Building Maintenance", "EXPENSE"),
        ]
        cursor.executemany("INSERT INTO account_heads (head_name, head_type) VALUES (%s,%s)", account_heads)

        # ---- Leave types -----------------------------------------------------
        leave_types = [("Casual Leave", 12), ("Sick Leave", 10), ("Earned Leave", 15), ("On-Duty", 30)]
        cursor.executemany("INSERT INTO leave_types (type_name, max_days_per_year) VALUES (%s,%s)", leave_types)

        # ---- Sample library books ---------------------------------------------
        books = [
            ("9780134685991", "Effective Java", "Joshua Bloch", "Addison-Wesley", "Computer Science", 3, 3, "R1-A"),
            ("9780262033848", "Introduction to Algorithms", "Cormen et al.", "MIT Press", "Computer Science", 2, 2, "R1-B"),
            ("9780141439600", "Pride and Prejudice", "Jane Austen", "Penguin Classics", "Fiction", 5, 5, "R2-A"),
            ("9780070635394", "NCERT Mathematics Class 9", "NCERT", "NCERT", "Textbook", 10, 10, "R3-A"),
        ]
        cursor.executemany("""
            INSERT INTO books (isbn, title, author, publisher, category, total_copies, available_copies, rack_no)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, books)

        # ---- Hostel rooms ---------------------------------------------------
        hostel_rooms = [
            ("Boys Hostel Block A", "101", "DOUBLE", 2, 3500.00),
            ("Boys Hostel Block A", "102", "DOUBLE", 2, 3500.00),
            ("Girls Hostel Block B", "201", "SINGLE", 1, 5000.00),
        ]
        cursor.executemany("""
            INSERT INTO hostel_rooms (hostel_name, room_no, room_type, capacity, monthly_rent)
            VALUES (%s,%s,%s,%s,%s)
        """, hostel_rooms)

        # ---- Salary template ---------------------------------------------------
        cursor.execute("""
            INSERT INTO salary_templates
                (template_name, basic_salary, hra, da, other_allowance, pf_deduction, tax_deduction, other_deduction)
            VALUES ('Standard PGT Template', 40000, 12000, 5000, 2000, 4800, 1500, 0)
        """)
        template_id = cursor.lastrowid
        cursor.execute("""
            INSERT INTO employee_salary_assignment (employee_id, template_id, effective_from)
            VALUES (%s, %s, '2025-04-01')
        """, (emp_map["EMP002"], template_id))

        # ---- Website content ------------------------------------------------
        cursor.execute("""
            INSERT INTO website_news (title, content, published_on, is_published)
            VALUES ('Annual Sports Day Announced', 'Our Annual Sports Day will be held on 20th December.', '2025-11-01', TRUE)
        """)
        cursor.execute("""
            INSERT INTO website_events (title, event_date, venue, description)
            VALUES ('Annual Day Function', '2025-12-20', 'School Auditorium', 'Cultural performances and prize distribution.')
        """)
        cursor.execute("""
            INSERT INTO notice_board (title, content, audience, expiry_date)
            VALUES ('PTM Notice', 'Parent Teacher Meeting scheduled for all classes.', 'PARENTS', '2025-09-30')
        """)
        cursor.execute("""
            INSERT INTO website_settings (setting_key, setting_value)
            VALUES ('GOOGLE_ANALYTICS_SCRIPT', '<!-- GA script placeholder: inject real tracking ID here -->')
        """)

        conn.commit()
        print("[OK] Seed data inserted successfully.")
        print_seed_credentials(seed_users)

    except Error as e:
        conn.rollback()
        print(f"[FATAL] Error while seeding data: {e}")
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()


def print_seed_credentials(seed_users):
    print("\n" + "=" * 60)
    print(" DEMO LOGIN CREDENTIALS (username / password)")
    print("=" * 60)
    for username, plain_pw, role_name, *_ in seed_users:
        print(f"  {role_name:<12} -> {username:<15} / {plain_pw}")
    print("=" * 60 + "\n")


# -------------------------------------------------------------------------
# 6. MAIN ENTRY POINT
# -------------------------------------------------------------------------
if __name__ == "__main__":
    print("Initializing School Management System database...\n")
    build_schema()
    seed_data()
    print("Database is ready. You can now run main.py (Step 3).")