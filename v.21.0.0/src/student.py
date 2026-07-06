"""
===============================================================================
 student.py
-------------------------------------------------------------------------------
 Covers:
   - Regular Student Admission (direct insert into `students`)
   - Online Admission Portal simulation: requests go into
     `online_admission_requests` first and must be Approved/Rejected by an
     admin, at which point Approve creates the real `students` row.
   - Student directory: search/filter by class & section, view details.
   - Promotion engine: dynamic pass/fail logic based on an exam's marks,
     rolling students to the next class for a new academic year, or
     detaining them, and logging every decision to
     `student_promotion_history`.
===============================================================================
"""

import tkinter as tk
from tkinter import ttk
from datetime import date

from db_config import get_connection
from utils import make_treeview, clear_tree, build_form, get_value, info, error, confirm, COLORS


# ---------------------------------------------------------------------------
# DATA ACCESS HELPERS
# ---------------------------------------------------------------------------
def fetch_classes():
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT class_id, class_name, class_order FROM classes ORDER BY class_order")
    rows = cur.fetchall(); cur.close(); conn.close()
    return rows


def fetch_sections(class_id):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT section_id, section_name FROM sections WHERE class_id=%s ORDER BY section_name", (class_id,))
    rows = cur.fetchall(); cur.close(); conn.close()
    return rows


def fetch_current_academic_year():
    conn = get_connection(); cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM academic_years WHERE is_current = TRUE LIMIT 1")
    row = cur.fetchone(); cur.close(); conn.close()
    return row


def next_admission_no():
    year = date.today().year
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM students WHERE admission_no LIKE %s", (f"ADM{year}%",))
    count = cur.fetchone()[0]
    cur.close(); conn.close()
    return f"ADM{year}{count + 1:03d}"


# ---------------------------------------------------------------------------
# MAIN STUDENT FRAME (tabbed: Directory / New Admission / Online Requests / Promotion)
# ---------------------------------------------------------------------------
class StudentModuleFrame(ttk.Frame):
    def __init__(self, parent, current_user):
        super().__init__(parent)
        self.current_user = current_user
        self.class_name_to_id = {}

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.directory_tab = ttk.Frame(notebook)
        self.admission_tab = ttk.Frame(notebook)
        self.online_tab = ttk.Frame(notebook)
        self.promotion_tab = ttk.Frame(notebook)

        notebook.add(self.directory_tab, text="Student Directory")
        notebook.add(self.admission_tab, text="New Admission")
        notebook.add(self.online_tab, text="Online Admission Requests")
        notebook.add(self.promotion_tab, text="Promotion Engine")

        self._build_directory_tab()
        self._build_admission_tab()
        self._build_online_tab()
        self._build_promotion_tab()

    # ------------------------------------------------------------------ #
    # TAB 1: DIRECTORY
    # ------------------------------------------------------------------ #
    def _build_directory_tab(self):
        top = ttk.Frame(self.directory_tab)
        top.pack(fill="x", padx=10, pady=10)

        ttk.Label(top, text="Search by name:").pack(side="left")
        self.search_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.search_var, width=25).pack(side="left", padx=5)
        ttk.Button(top, text="Search", command=self._load_directory).pack(side="left", padx=5)
        ttk.Button(top, text="Show All", command=lambda: (self.search_var.set(""), self._load_directory())
                   ).pack(side="left")

        cols = ("adm_no", "name", "class", "section", "gender", "roll", "status")
        headings = {"adm_no": "Admission No", "name": "Name", "class": "Class",
                    "section": "Sec", "gender": "Gender", "roll": "Roll No", "status": "Status"}
        widths = {"adm_no": 100, "name": 160, "class": 80, "section": 50, "gender": 70, "roll": 60, "status": 90}
        self.dir_tree, container = make_treeview(self.directory_tab, cols, headings, widths)
        container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self._load_directory()

    def _load_directory(self):
        clear_tree(self.dir_tree)
        keyword = f"%{self.search_var.get().strip()}%"
        conn = get_connection(); cur = conn.cursor()
        cur.execute("""
            SELECT s.admission_no, CONCAT(s.first_name,' ',IFNULL(s.last_name,'')),
                   c.class_name, sec.section_name, s.gender, s.roll_no, s.status
            FROM students s
            JOIN classes c ON c.class_id = s.class_id
            JOIN sections sec ON sec.section_id = s.section_id
            WHERE CONCAT(s.first_name,' ',IFNULL(s.last_name,'')) LIKE %s
            ORDER BY c.class_order, sec.section_name, s.roll_no
        """, (keyword,))
        for row in cur.fetchall():
            self.dir_tree.insert("", "end", values=row)
        cur.close(); conn.close()

    # ------------------------------------------------------------------ #
    # TAB 2: NEW (REGULAR) ADMISSION
    # ------------------------------------------------------------------ #
    def _build_admission_tab(self):
        ttk.Label(self.admission_tab, text="Regular Student Admission Form",
                  style="SubHeader.TLabel").pack(anchor="w", padx=15, pady=10)

        form_frame = ttk.Frame(self.admission_tab)
        form_frame.pack(padx=15, pady=5, anchor="w")

        classes = fetch_classes()
        class_opts = ",".join(c[1] for c in classes)
        self.class_name_to_id = {c[1]: c[0] for c in classes}

        fields = [
            ("first_name", "First Name", "entry"),
            ("last_name", "Last Name", "entry"),
            ("dob", "Date of Birth (YYYY-MM-DD)", "entry"),
            ("gender", "Gender", "combo:MALE,FEMALE,OTHER"),
            ("class_name", "Class", f"combo:{class_opts}"),
            ("father_name", "Father's Name", "entry"),
            ("mother_name", "Mother's Name", "entry"),
            ("phone", "Guardian Phone", "entry"),
            ("email", "Guardian Email", "entry"),
            ("address", "Address", "entry"),
        ]
        self.adm_widgets = build_form(form_frame, fields)
        # Section combo depends on class selection -> refresh dynamically
        self.adm_widgets["class_name"].bind("<<ComboboxSelected>>", self._refresh_sections_for_admission)

        ttk.Label(form_frame, text="Section:").grid(row=len(fields), column=0, sticky="e", padx=6, pady=5)
        self.section_var = tk.StringVar()
        self.section_combo = ttk.Combobox(form_frame, textvariable=self.section_var, state="readonly", width=27)
        self.section_combo.grid(row=len(fields), column=1, sticky="w", padx=6, pady=5)

        ttk.Button(self.admission_tab, text="Submit Admission", style="Accent.TButton",
                   command=self._submit_admission).pack(pady=15)

    def _refresh_sections_for_admission(self, event=None):
        class_id = self.class_name_to_id.get(get_value(self.adm_widgets["class_name"]))
        if not class_id:
            return
        sections = fetch_sections(class_id)
        self.section_combo["values"] = [s[1] for s in sections]
        if sections:
            self.section_var.set(sections[0][1])

    def _submit_admission(self):
        data = {k: get_value(w) for k, w in self.adm_widgets.items()}
        section_name = self.section_var.get()

        if not data["first_name"] or not data["dob"] or section_name == "":
            error("Missing Data", "First name, date of birth, and section are required.")
            return

        class_id = self.class_name_to_id.get(data["class_name"])
        year = fetch_current_academic_year()
        if not class_id or not year:
            error("Setup Error", "Class or current academic year not configured.")
            return

        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT section_id FROM sections WHERE class_id=%s AND section_name=%s",
                    (class_id, section_name))
        sec_row = cur.fetchone()
        if not sec_row:
            error("Setup Error", "Section not found for selected class.")
            cur.close(); conn.close()
            return
        section_id = sec_row[0]

        cur.execute("SELECT IFNULL(MAX(roll_no),0)+1 FROM students WHERE class_id=%s AND section_id=%s",
                    (class_id, section_id))
        roll_no = cur.fetchone()[0]

        admission_no = next_admission_no()
        try:
            cur.execute("""
                INSERT INTO students
                    (admission_no, first_name, last_name, dob, gender, address, phone, email,
                     father_name, mother_name, class_id, section_id, academic_year_id,
                     roll_no, admission_date, admission_mode, status)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'REGULAR','ACTIVE')
            """, (admission_no, data["first_name"], data["last_name"], data["dob"], data["gender"],
                  data["address"], data["phone"], data["email"], data["father_name"], data["mother_name"],
                  class_id, section_id, year["academic_year_id"], roll_no, date.today()))
            conn.commit()
            info("Admission Successful", f"Student admitted successfully.\nAdmission No: {admission_no}\nRoll No: {roll_no}")
            self._load_directory()
        except Exception as e:
            conn.rollback()
            error("Database Error", str(e))
        finally:
            cur.close(); conn.close()

    # ------------------------------------------------------------------ #
    # TAB 3: ONLINE ADMISSION REQUESTS (approve -> creates real student)
    # ------------------------------------------------------------------ #
    def _build_online_tab(self):
        top = ttk.Frame(self.online_tab)
        top.pack(fill="x", padx=10, pady=10)
        ttk.Button(top, text="Refresh Pending Requests", command=self._load_online_requests).pack(side="left")
        ttk.Button(top, text="Approve Selected", command=self._approve_online_request).pack(side="left", padx=5)
        ttk.Button(top, text="Reject Selected", command=self._reject_online_request).pack(side="left")

        cols = ("id", "name", "dob", "gender", "class", "phone", "email", "status")
        widths = {"id": 40, "name": 150, "dob": 90, "gender": 70, "class": 80, "phone": 100, "email": 160, "status": 80}
        self.online_tree, container = make_treeview(self.online_tab, cols, widths=widths)
        container.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self._load_online_requests()

    def _load_online_requests(self):
        clear_tree(self.online_tree)
        conn = get_connection(); cur = conn.cursor()
        cur.execute("""
            SELECT r.request_id, CONCAT(r.first_name,' ',IFNULL(r.last_name,'')), r.dob, r.gender,
                   c.class_name, r.contact_phone, r.contact_email, r.status
            FROM online_admission_requests r
            JOIN classes c ON c.class_id = r.applying_class_id
            WHERE r.status = 'PENDING'
            ORDER BY r.submitted_on
        """)
        for row in cur.fetchall():
            self.online_tree.insert("", "end", values=row)
        cur.close(); conn.close()

    def _get_selected_request_id(self):
        sel = self.online_tree.selection()
        if not sel:
            error("No Selection", "Please select a request first.")
            return None
        return self.online_tree.item(sel[0])["values"][0]

    def _approve_online_request(self):
        request_id = self._get_selected_request_id()
        if not request_id:
            return
        if not confirm("Confirm Approval", "Approve this request and create a student record?"):
            return

        conn = get_connection(); cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM online_admission_requests WHERE request_id=%s", (request_id,))
        req = cur.fetchone()
        year = fetch_current_academic_year()

        cur.execute("SELECT section_id FROM sections WHERE class_id=%s ORDER BY section_id LIMIT 1",
                    (req["applying_class_id"],))
        sec = cur.fetchone()
        if not sec:
            error("Setup Error", "No section configured for the applied class.")
            cur.close(); conn.close()
            return

        cur.execute("SELECT IFNULL(MAX(roll_no),0)+1 FROM students WHERE class_id=%s AND section_id=%s",
                    (req["applying_class_id"], sec["section_id"]))
        roll_no = cur.fetchone()["IFNULL(MAX(roll_no),0)+1"]
        admission_no = next_admission_no()

        try:
            cur.execute("""
                INSERT INTO students
                    (admission_no, first_name, last_name, dob, gender, phone, email,
                     father_name, mother_name, class_id, section_id, academic_year_id,
                     roll_no, admission_date, admission_mode, status)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'ONLINE','ACTIVE')
            """, (admission_no, req["first_name"], req["last_name"], req["dob"], req["gender"],
                  req["contact_phone"], req["contact_email"], req["father_name"], req["mother_name"],
                  req["applying_class_id"], sec["section_id"], year["academic_year_id"], roll_no, date.today()))
            cur.execute("UPDATE online_admission_requests SET status='APPROVED' WHERE request_id=%s", (request_id,))
            conn.commit()
            info("Approved", f"Student created with Admission No: {admission_no}")
            self._load_online_requests()
            self._load_directory()
        except Exception as e:
            conn.rollback()
            error("Database Error", str(e))
        finally:
            cur.close(); conn.close()

    def _reject_online_request(self):
        request_id = self._get_selected_request_id()
        if not request_id:
            return
        conn = get_connection(); cur = conn.cursor()
        cur.execute("UPDATE online_admission_requests SET status='REJECTED' WHERE request_id=%s", (request_id,))
        conn.commit(); cur.close(); conn.close()
        self._load_online_requests()

    # ------------------------------------------------------------------ #
    # TAB 4: PROMOTION ENGINE
    #   Dynamic pass/fail logic:
    #     - Pick a "final" exam for the current academic year.
    #     - For every student in the source class, compute % across all
    #       subjects in that exam AND check that no single subject fell
    #       below its configured min_pass_marks.
    #     - If pass_percent_threshold is met AND no subject failure ->
    #       PROMOTED to next class_order in the new academic year.
    #     - Else -> DETAINED (same class, new academic year).
    #     - Every decision is logged in student_promotion_history.
    # ------------------------------------------------------------------ #
    def _build_promotion_tab(self):
        frame = ttk.Frame(self.promotion_tab)
        frame.pack(fill="x", padx=15, pady=15)

        classes = fetch_classes()
        self.promo_class_map = {c[1]: c[0] for c in classes}

        ttk.Label(frame, text="From Class:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.promo_class_var = tk.StringVar()
        ttk.Combobox(frame, textvariable=self.promo_class_var, values=list(self.promo_class_map),
                     state="readonly", width=20).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(frame, text="Exam (used for result):").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.promo_exam_var = tk.StringVar()
        self.exam_combo = ttk.Combobox(frame, textvariable=self.promo_exam_var, state="readonly", width=20)
        self.exam_combo.grid(row=1, column=1, padx=5, pady=5)
        self._load_exam_list()

        ttk.Label(frame, text="Passing Percentage:").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        self.promo_threshold_var = tk.StringVar(value="33")
        ttk.Entry(frame, textvariable=self.promo_threshold_var, width=10).grid(row=2, column=1, sticky="w", padx=5)

        ttk.Label(frame, text="New Academic Year Label (e.g. 2026-2027):").grid(row=3, column=0, sticky="e", padx=5, pady=5)
        self.new_year_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.new_year_var, width=20).grid(row=3, column=1, sticky="w", padx=5)

        ttk.Button(frame, text="Preview Promotion Results", command=self._preview_promotion).grid(
            row=4, column=0, columnspan=2, pady=10)
        ttk.Button(frame, text="Commit Promotion (writes to DB)", style="Accent.TButton",
                   command=self._commit_promotion).grid(row=5, column=0, columnspan=2, pady=(0, 10))

        cols = ("adm_no", "name", "percent", "min_subject", "result")
        self.promo_tree, container = make_treeview(self.promotion_tab, cols, height=12)
        container.pack(fill="both", expand=True, padx=15, pady=10)

        self._promotion_preview_cache = {}

    def _load_exam_list(self):
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT exam_id, exam_name FROM exams ORDER BY exam_id DESC")
        rows = cur.fetchall(); cur.close(); conn.close()
        self.exam_id_map = {r[1]: r[0] for r in rows}
        self.exam_combo["values"] = list(self.exam_id_map)

    def _compute_results(self):
        """Returns dict: student_id -> (name, admission_no, percent, min_subject_marks_pct, result)"""
        class_id = self.promo_class_map.get(self.promo_class_var.get())
        exam_id = self.exam_id_map.get(self.promo_exam_var.get())
        try:
            threshold = float(self.promo_threshold_var.get())
        except ValueError:
            threshold = 33.0

        if not class_id or not exam_id:
            error("Missing Selection", "Please choose both a class and an exam.")
            return {}

        conn = get_connection(); cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT s.student_id, s.admission_no, s.first_name, s.last_name
            FROM students s WHERE s.class_id=%s AND s.status='ACTIVE'
        """, (class_id,))
        students = cur.fetchall()

        results = {}
        for stu in students:
            cur.execute("""
                SELECT es.max_marks, es.min_pass_marks, IFNULL(m.marks_obtained,0) AS obtained
                FROM exam_schedule es
                LEFT JOIN student_marks m ON m.schedule_id = es.schedule_id AND m.student_id = %s
                WHERE es.exam_id=%s AND es.class_id=%s
            """, (stu["student_id"], exam_id, class_id))
            subject_rows = cur.fetchall()

            if not subject_rows:
                results[stu["student_id"]] = (stu["admission_no"],
                                               f"{stu['first_name']} {stu['last_name'] or ''}",
                                               0.0, "NO DATA", "DETAINED")
                continue

            total_max = sum(r["max_marks"] for r in subject_rows)
            total_obt = sum(r["obtained"] for r in subject_rows)
            percent = round((total_obt / total_max) * 100, 2) if total_max else 0.0
            subject_failed = any(r["obtained"] < r["min_pass_marks"] for r in subject_rows)

            result = "PROMOTED" if (percent >= threshold and not subject_failed) else "DETAINED"
            results[stu["student_id"]] = (stu["admission_no"], f"{stu['first_name']} {stu['last_name'] or ''}",
                                           percent, "FAIL" if subject_failed else "OK", result)
        cur.close(); conn.close()
        return results

    def _preview_promotion(self):
        clear_tree(self.promo_tree)
        results = self._compute_results()
        self._promotion_preview_cache = results
        for student_id, (adm_no, name, percent, min_subj, result) in results.items():
            self.promo_tree.insert("", "end", values=(adm_no, name, f"{percent}%", min_subj, result))

    def _commit_promotion(self):
        if not self._promotion_preview_cache:
            error("Nothing to Commit", "Please run 'Preview Promotion Results' first.")
            return
        new_year_label = self.new_year_var.get().strip()
        if not new_year_label:
            error("Missing Data", "Please enter the new academic year label.")
            return
        if not confirm("Confirm Promotion", "This will update student records permanently. Continue?"):
            return

        class_id = self.promo_class_map.get(self.promo_class_var.get())
        conn = get_connection(); cur = conn.cursor()

        # Ensure new academic year exists (create a placeholder one if not found)
        cur.execute("SELECT academic_year_id FROM academic_years WHERE year_label=%s", (new_year_label,))
        row = cur.fetchone()
        if row:
            new_year_id = row[0]
        else:
            start_year = new_year_label.split("-")[0]
            cur.execute("""
                INSERT INTO academic_years (year_label, start_date, end_date, is_current)
                VALUES (%s, %s, %s, FALSE)
            """, (new_year_label, f"{start_year}-04-01", f"{int(start_year)+1}-03-31"))
            new_year_id = cur.lastrowid

        cur.execute("SELECT academic_year_id FROM academic_years WHERE is_current=TRUE")
        current_year_id = cur.fetchone()[0]

        cur.execute("SELECT class_id, class_order FROM classes WHERE class_id=%s", (class_id,))
        _, current_order = cur.fetchone()
        cur.execute("SELECT class_id FROM classes WHERE class_order=%s", (current_order + 1,))
        next_class_row = cur.fetchone()
        next_class_id = next_class_row[0] if next_class_row else class_id  # Class 12 has nowhere to go -> GRADUATED handled below

        try:
            for student_id, (adm_no, name, percent, min_subj, result) in self._promotion_preview_cache.items():
                if result == "PROMOTED" and next_class_row:
                    target_class = next_class_id
                    new_status = "ACTIVE"
                    history_result = "PROMOTED"
                elif result == "PROMOTED" and not next_class_row:
                    target_class = class_id
                    new_status = "GRADUATED"
                    history_result = "GRADUATED"
                else:
                    target_class = class_id
                    new_status = "ACTIVE"
                    history_result = "DETAINED"

                cur.execute("SELECT section_id FROM sections WHERE class_id=%s ORDER BY section_id LIMIT 1",
                            (target_class,))
                sec = cur.fetchone()
                section_id = sec[0] if sec else None

                cur.execute("""
                    INSERT INTO student_promotion_history
                        (student_id, from_academic_year_id, to_academic_year_id, from_class_id,
                         to_class_id, result, percentage, remarks)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                """, (student_id, current_year_id, new_year_id, class_id, target_class,
                      history_result, percent, min_subj))

                if history_result != "GRADUATED":
                    cur.execute("""
                        UPDATE students SET class_id=%s, section_id=%s, academic_year_id=%s, status=%s
                        WHERE student_id=%s
                    """, (target_class, section_id, new_year_id, new_status, student_id))
                else:
                    cur.execute("UPDATE students SET status='GRADUATED' WHERE student_id=%s", (student_id,))

            conn.commit()
            info("Promotion Complete", "Students have been promoted/detained and history logged.")
            self._load_directory()
        except Exception as e:
            conn.rollback()
            error("Database Error", str(e))
        finally:
            cur.close(); conn.close()