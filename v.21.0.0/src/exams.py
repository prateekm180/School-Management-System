"""
===============================================================================
 exams.py
-------------------------------------------------------------------------------
 Covers:
   - Exam Setup: create an exam, and its per-class-per-subject schedule with
     configurable max_marks / min_pass_marks (Exam & Grading Rules config).
   - Easy Marks Entry console: pick exam+class+subject, enter marks for every
     enrolled student in one grid.
   - Automated Report Card Generation: computes total/percentage/grade
     (via `grading_scale`) and overall PASS/FAIL for a chosen student+exam.
===============================================================================
"""

import tkinter as tk
from tkinter import ttk
from datetime import date

from db_config import get_connection
from utils import make_treeview, clear_tree, info, error


class ExamModuleFrame(ttk.Frame):
    def __init__(self, parent, current_user):
        super().__init__(parent)
        self.current_user = current_user

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.setup_tab = ttk.Frame(notebook)
        self.marks_tab = ttk.Frame(notebook)
        self.report_tab = ttk.Frame(notebook)

        notebook.add(self.setup_tab, text="Exam & Grading Setup")
        notebook.add(self.marks_tab, text="Marks Entry")
        notebook.add(self.report_tab, text="Report Card")

        self._load_lookups()
        self._build_setup_tab()
        self._build_marks_tab()
        self._build_report_tab()

    def _load_lookups(self):
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT class_id, class_name FROM classes ORDER BY class_order")
        self.class_map = {name: cid for cid, name in cur.fetchall()}
        cur.execute("SELECT subject_id, subject_name FROM subjects ORDER BY subject_name")
        self.subject_map = {name: sid for sid, name in cur.fetchall()}
        cur.execute("SELECT academic_year_id FROM academic_years WHERE is_current=TRUE")
        row = cur.fetchone()
        self.current_year_id = row[0] if row else None
        cur.close(); conn.close()

    # ------------------------------------------------------------------ #
    # TAB 1: EXAM + SCHEDULE (GRADING RULES) SETUP
    # ------------------------------------------------------------------ #
    def _build_setup_tab(self):
        form = ttk.Frame(self.setup_tab)
        form.pack(fill="x", padx=15, pady=15)

        ttk.Label(form, text="Exam Name:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.exam_name_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.exam_name_var, width=25).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(form, text="Create Exam", command=self._create_exam).grid(row=0, column=2, padx=10)

        ttk.Separator(self.setup_tab, orient="horizontal").pack(fill="x", padx=15, pady=10)

        ttk.Label(self.setup_tab, text="Add Subject to an Exam's Schedule (Grading Rule)",
                  style="SubHeader.TLabel").pack(anchor="w", padx=15)

        form2 = ttk.Frame(self.setup_tab)
        form2.pack(fill="x", padx=15, pady=10)

        ttk.Label(form2, text="Exam:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.schedule_exam_var = tk.StringVar()
        self.schedule_exam_combo = ttk.Combobox(form2, textvariable=self.schedule_exam_var,
                                                 state="readonly", width=20)
        self.schedule_exam_combo.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(form2, text="Class:").grid(row=0, column=2, sticky="e", padx=5, pady=5)
        self.schedule_class_var = tk.StringVar()
        ttk.Combobox(form2, textvariable=self.schedule_class_var, values=list(self.class_map),
                     state="readonly", width=15).grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(form2, text="Subject:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.schedule_subject_var = tk.StringVar()
        ttk.Combobox(form2, textvariable=self.schedule_subject_var, values=list(self.subject_map),
                     state="readonly", width=20).grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(form2, text="Max Marks:").grid(row=1, column=2, sticky="e", padx=5, pady=5)
        self.max_marks_var = tk.StringVar(value="100")
        ttk.Entry(form2, textvariable=self.max_marks_var, width=10).grid(row=1, column=3, sticky="w", padx=5)

        ttk.Label(form2, text="Min Pass Marks:").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        self.min_pass_var = tk.StringVar(value="33")
        ttk.Entry(form2, textvariable=self.min_pass_var, width=10).grid(row=2, column=1, sticky="w", padx=5)

        ttk.Button(form2, text="Add to Schedule", style="Accent.TButton",
                   command=self._add_schedule).grid(row=2, column=3, pady=5)

        self._refresh_exam_list()

    def _refresh_exam_list(self):
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT exam_id, exam_name FROM exams ORDER BY exam_id DESC")
        rows = cur.fetchall(); cur.close(); conn.close()
        self.exam_id_map = {name: eid for eid, name in rows}
        self.schedule_exam_combo["values"] = list(self.exam_id_map)
        if hasattr(self, "marks_exam_combo"):
            self.marks_exam_combo["values"] = list(self.exam_id_map)
        if hasattr(self, "report_exam_combo"):
            self.report_exam_combo["values"] = list(self.exam_id_map)

    def _create_exam(self):
        name = self.exam_name_var.get().strip()
        if not name or not self.current_year_id:
            error("Missing Data", "Enter an exam name (and ensure a current academic year exists).")
            return
        conn = get_connection(); cur = conn.cursor()
        cur.execute("INSERT INTO exams (exam_name, academic_year_id) VALUES (%s,%s)",
                    (name, self.current_year_id))
        conn.commit(); cur.close(); conn.close()
        info("Created", f"Exam '{name}' created.")
        self.exam_name_var.set("")
        self._refresh_exam_list()

    def _add_schedule(self):
        exam_id = self.exam_id_map.get(self.schedule_exam_var.get())
        class_id = self.class_map.get(self.schedule_class_var.get())
        subject_id = self.subject_map.get(self.schedule_subject_var.get())
        if not (exam_id and class_id and subject_id):
            error("Missing Data", "Please select exam, class and subject.")
            return
        try:
            max_marks = int(self.max_marks_var.get())
            min_pass = int(self.min_pass_var.get())
        except ValueError:
            error("Invalid Input", "Max marks / min pass marks must be numbers.")
            return

        conn = get_connection(); cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO exam_schedule (exam_id, class_id, subject_id, max_marks, min_pass_marks)
                VALUES (%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE max_marks=VALUES(max_marks), min_pass_marks=VALUES(min_pass_marks)
            """, (exam_id, class_id, subject_id, max_marks, min_pass))
            conn.commit()
            info("Saved", "Exam schedule / grading rule saved.")
        except Exception as e:
            conn.rollback()
            error("Database Error", str(e))
        finally:
            cur.close(); conn.close()

    # ------------------------------------------------------------------ #
    # TAB 2: MARKS ENTRY CONSOLE
    # ------------------------------------------------------------------ #
    def _build_marks_tab(self):
        top = ttk.Frame(self.marks_tab)
        top.pack(fill="x", padx=10, pady=10)

        ttk.Label(top, text="Exam:").pack(side="left")
        self.marks_exam_var = tk.StringVar()
        self.marks_exam_combo = ttk.Combobox(top, textvariable=self.marks_exam_var,
                                              values=list(self.exam_id_map), state="readonly", width=18)
        self.marks_exam_combo.pack(side="left", padx=5)

        ttk.Label(top, text="Class:").pack(side="left")
        self.marks_class_var = tk.StringVar()
        ttk.Combobox(top, textvariable=self.marks_class_var, values=list(self.class_map),
                     state="readonly", width=15).pack(side="left", padx=5)

        ttk.Label(top, text="Subject:").pack(side="left")
        self.marks_subject_var = tk.StringVar()
        ttk.Combobox(top, textvariable=self.marks_subject_var, values=list(self.subject_map),
                     state="readonly", width=18).pack(side="left", padx=5)

        ttk.Button(top, text="Load Students", command=self._load_students_for_marks).pack(side="left", padx=10)
        ttk.Button(top, text="Save Marks", style="Accent.TButton", command=self._save_marks).pack(side="left")

        cols = ("id", "name", "roll", "marks")
        self.marks_tree, container = make_treeview(self.marks_tab, cols, height=15)
        container.pack(fill="both", expand=True, padx=10, pady=10)
        self.marks_tree.bind("<Double-1>", self._edit_marks_cell)
        ttk.Label(self.marks_tab, text="Tip: double-click a row's Marks cell to type a value.",
                  foreground="#666666").pack(anchor="w", padx=10)

    def _load_students_for_marks(self):
        clear_tree(self.marks_tree)
        exam_id = self.exam_id_map.get(self.marks_exam_var.get())
        class_id = self.class_map.get(self.marks_class_var.get())
        subject_id = self.subject_map.get(self.marks_subject_var.get())
        if not (exam_id and class_id and subject_id):
            error("Missing Selection", "Please choose exam, class and subject.")
            return

        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT schedule_id FROM exam_schedule WHERE exam_id=%s AND class_id=%s AND subject_id=%s",
                    (exam_id, class_id, subject_id))
        row = cur.fetchone()
        if not row:
            error("Not Configured", "This exam/class/subject combination has no schedule yet. "
                                     "Add it first under 'Exam & Grading Setup'.")
            cur.close(); conn.close()
            return
        self._current_schedule_id = row[0]

        cur.execute("""
            SELECT s.student_id, CONCAT(s.first_name,' ',IFNULL(s.last_name,'')), s.roll_no,
                   IFNULL(m.marks_obtained, '')
            FROM students s
            LEFT JOIN student_marks m ON m.student_id = s.student_id AND m.schedule_id = %s
            WHERE s.class_id=%s AND s.status='ACTIVE'
            ORDER BY s.roll_no
        """, (self._current_schedule_id, class_id))
        for sid, name, roll, marks in cur.fetchall():
            self.marks_tree.insert("", "end", values=(sid, name, roll, marks))
        cur.close(); conn.close()

    def _edit_marks_cell(self, event):
        item = self.marks_tree.identify_row(event.y)
        col = self.marks_tree.identify_column(event.x)
        if not item or col != "#4":
            return
        x, y, w, h = self.marks_tree.bbox(item, col)
        current = self.marks_tree.set(item, "marks")
        entry = tk.Entry(self.marks_tree)
        entry.place(x=x, y=y, width=w, height=h)
        entry.insert(0, current)
        entry.focus_set()

        def save_edit(event=None):
            self.marks_tree.set(item, "marks", entry.get())
            entry.destroy()

        entry.bind("<Return>", save_edit)
        entry.bind("<FocusOut>", save_edit)

    def _save_marks(self):
        if not hasattr(self, "_current_schedule_id"):
            error("Not Loaded", "Load students first.")
            return
        rows = [self.marks_tree.item(i)["values"] for i in self.marks_tree.get_children()]
        conn = get_connection(); cur = conn.cursor()
        try:
            saved = 0
            for student_id, name, roll, marks in rows:
                if str(marks).strip() == "":
                    continue
                cur.execute("""
                    INSERT INTO student_marks (student_id, schedule_id, marks_obtained, entered_by)
                    VALUES (%s,%s,%s,%s)
                    ON DUPLICATE KEY UPDATE marks_obtained=VALUES(marks_obtained), entered_by=VALUES(entered_by)
                """, (student_id, self._current_schedule_id, float(marks), self.current_user.linked_employee_id))
                saved += 1
            conn.commit()
            info("Saved", f"Marks saved for {saved} students.")
        except Exception as e:
            conn.rollback()
            error("Database Error", str(e))
        finally:
            cur.close(); conn.close()

    # ------------------------------------------------------------------ #
    # TAB 3: AUTOMATED REPORT CARD
    # ------------------------------------------------------------------ #
    def _build_report_tab(self):
        top = ttk.Frame(self.report_tab)
        top.pack(fill="x", padx=10, pady=10)

        ttk.Label(top, text="Admission No:").pack(side="left")
        self.report_adm_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.report_adm_var, width=15).pack(side="left", padx=5)

        ttk.Label(top, text="Exam:").pack(side="left")
        self.report_exam_var = tk.StringVar()
        self.report_exam_combo = ttk.Combobox(top, textvariable=self.report_exam_var,
                                               values=list(self.exam_id_map), state="readonly", width=18)
        self.report_exam_combo.pack(side="left", padx=5)

        ttk.Button(top, text="Generate Report Card", style="Accent.TButton",
                   command=self._generate_report_card).pack(side="left", padx=10)

        self.report_box = tk.Text(self.report_tab, height=25, font=("Consolas", 10))
        self.report_box.pack(fill="both", expand=True, padx=10, pady=10)

    def _generate_report_card(self):
        adm_no = self.report_adm_var.get().strip()
        exam_id = self.exam_id_map.get(self.report_exam_var.get())
        if not adm_no or not exam_id:
            error("Missing Data", "Enter admission number and select an exam.")
            return

        conn = get_connection(); cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM students WHERE admission_no=%s", (adm_no,))
        student = cur.fetchone()
        if not student:
            error("Not Found", "No student with that admission number.")
            cur.close(); conn.close()
            return

        cur.execute("""
            SELECT sub.subject_name, es.max_marks, es.min_pass_marks, IFNULL(m.marks_obtained,0) AS obtained
            FROM exam_schedule es
            JOIN subjects sub ON sub.subject_id = es.subject_id
            LEFT JOIN student_marks m ON m.schedule_id = es.schedule_id AND m.student_id = %s
            WHERE es.exam_id=%s AND es.class_id=%s
            ORDER BY sub.subject_name
        """, (student["student_id"], exam_id, student["class_id"]))
        subject_rows = cur.fetchall()

        if not subject_rows:
            error("No Data", "No exam schedule/marks found for this student's class.")
            cur.close(); conn.close()
            return

        cur.execute("SELECT * FROM grading_scale ORDER BY min_percent DESC")
        grading_scale = cur.fetchall()

        cur.execute("SELECT exam_name FROM exams WHERE exam_id=%s", (exam_id,))
        exam_name = cur.fetchone()["exam_name"]
        cur.close(); conn.close()

        def grade_for(pct):
            for g in grading_scale:
                if g["min_percent"] <= pct <= g["max_percent"]:
                    return g["grade_label"], g["remark"]
            return "-", "-"

        total_max = sum(r["max_marks"] for r in subject_rows)
        total_obt = sum(r["obtained"] for r in subject_rows)
        overall_pct = round((total_obt / total_max) * 100, 2) if total_max else 0
        overall_grade, overall_remark = grade_for(overall_pct)
        subject_failed = any(r["obtained"] < r["min_pass_marks"] for r in subject_rows)
        final_result = "FAIL" if subject_failed else "PASS"

        lines = []
        lines.append("=" * 60)
        lines.append(f"{'REPORT CARD':^60}")
        lines.append("=" * 60)
        lines.append(f"Student   : {student['first_name']} {student['last_name'] or ''}")
        lines.append(f"Admission : {student['admission_no']}")
        lines.append(f"Exam      : {exam_name}")
        lines.append("-" * 60)
        lines.append(f"{'Subject':<25}{'Max':>8}{'Obtained':>10}{'Grade':>10}")
        lines.append("-" * 60)
        for r in subject_rows:
            pct = (r["obtained"] / r["max_marks"]) * 100 if r["max_marks"] else 0
            grade, _ = grade_for(pct)
            status = "" if r["obtained"] >= r["min_pass_marks"] else "  (FAIL)"
            lines.append(f"{r['subject_name']:<25}{r['max_marks']:>8}{r['obtained']:>10}{grade:>10}{status}")
        lines.append("-" * 60)
        lines.append(f"Total: {total_obt}/{total_max}   Percentage: {overall_pct}%")
        lines.append(f"Overall Grade: {overall_grade} ({overall_remark})")
        lines.append(f"RESULT: {final_result}")
        lines.append("=" * 60)

        self.report_box.delete("1.0", "end")
        self.report_box.insert("1.0", "\n".join(lines))