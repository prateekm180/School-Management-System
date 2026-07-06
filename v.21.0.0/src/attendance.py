"""
===============================================================================
 attendance.py
-------------------------------------------------------------------------------
 Covers:
   - Daily Student Attendance (per class/section/date)
   - Daily Employee Attendance (incl. ON_DUTY / work-outside logging)
   - Employee Leave application + approval workflow
   - Attendance Notification Simulator: for a chosen date, finds all
     ABSENT students and "sends" a simulated Email/SMS to their guardian,
     logging each message into `notification_log`.
===============================================================================
"""

import tkinter as tk
from tkinter import ttk
from datetime import date

from db_config import get_connection
from utils import make_treeview, clear_tree, info, error, confirm, COLORS


class AttendanceModuleFrame(ttk.Frame):
    def __init__(self, parent, current_user):
        super().__init__(parent)
        self.current_user = current_user

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.student_tab = ttk.Frame(notebook)
        self.employee_tab = ttk.Frame(notebook)
        self.leave_tab = ttk.Frame(notebook)
        self.notify_tab = ttk.Frame(notebook)

        notebook.add(self.student_tab, text="Student Attendance")
        notebook.add(self.employee_tab, text="Employee Attendance")
        notebook.add(self.leave_tab, text="Employee Leave")
        notebook.add(self.notify_tab, text="Absentee Notification Simulator")

        self._build_student_tab()
        self._build_employee_tab()
        self._build_leave_tab()
        self._build_notify_tab()

    # ------------------------------------------------------------------ #
    # STUDENT ATTENDANCE
    # ------------------------------------------------------------------ #
    def _build_student_tab(self):
        top = ttk.Frame(self.student_tab)
        top.pack(fill="x", padx=10, pady=10)

        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT class_id, class_name FROM classes ORDER BY class_order")
        classes = cur.fetchall(); cur.close(); conn.close()
        self.att_class_map = {c[1]: c[0] for c in classes}

        ttk.Label(top, text="Class:").pack(side="left")
        self.att_class_var = tk.StringVar()
        class_combo = ttk.Combobox(top, textvariable=self.att_class_var, values=list(self.att_class_map),
                                    state="readonly", width=15)
        class_combo.pack(side="left", padx=5)
        class_combo.bind("<<ComboboxSelected>>", self._refresh_att_sections)

        ttk.Label(top, text="Section:").pack(side="left")
        self.att_section_var = tk.StringVar()
        self.att_section_combo = ttk.Combobox(top, textvariable=self.att_section_var, state="readonly", width=10)
        self.att_section_combo.pack(side="left", padx=5)

        ttk.Label(top, text="Date (YYYY-MM-DD):").pack(side="left")
        self.att_date_var = tk.StringVar(value=str(date.today()))
        ttk.Entry(top, textvariable=self.att_date_var, width=12).pack(side="left", padx=5)

        ttk.Button(top, text="Load Students", command=self._load_students_for_attendance).pack(side="left", padx=10)
        ttk.Button(top, text="Save Attendance", style="Accent.TButton",
                   command=self._save_student_attendance).pack(side="left")

        cols = ("id", "name", "roll", "status")
        self.att_tree, container = make_treeview(self.student_tab, cols, height=15)
        container.pack(fill="both", expand=True, padx=10, pady=10)
        self.att_tree.bind("<Double-1>", self._cycle_attendance_status)

        ttk.Label(self.student_tab, text="Tip: double-click a row to cycle PRESENT -> ABSENT -> LATE -> LEAVE",
                  foreground="#666666").pack(anchor="w", padx=10)

    def _refresh_att_sections(self, event=None):
        class_id = self.att_class_map.get(self.att_class_var.get())
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT section_name FROM sections WHERE class_id=%s ORDER BY section_name", (class_id,))
        sections = [r[0] for r in cur.fetchall()]
        cur.close(); conn.close()
        self.att_section_combo["values"] = sections
        if sections:
            self.att_section_var.set(sections[0])

    def _load_students_for_attendance(self):
        clear_tree(self.att_tree)
        class_id = self.att_class_map.get(self.att_class_var.get())
        section_name = self.att_section_var.get()
        if not class_id or not section_name:
            error("Missing Selection", "Please choose a class and section.")
            return
        conn = get_connection(); cur = conn.cursor()
        cur.execute("""
            SELECT s.student_id, CONCAT(s.first_name,' ',IFNULL(s.last_name,'')), s.roll_no
            FROM students s
            JOIN sections sec ON sec.section_id = s.section_id
            WHERE s.class_id=%s AND sec.section_name=%s AND s.status='ACTIVE'
            ORDER BY s.roll_no
        """, (class_id, section_name))
        for sid, name, roll in cur.fetchall():
            self.att_tree.insert("", "end", values=(sid, name, roll, "PRESENT"))
        cur.close(); conn.close()

    def _cycle_attendance_status(self, event):
        sel = self.att_tree.selection()
        if not sel:
            return
        cycle = ["PRESENT", "ABSENT", "LATE", "LEAVE"]
        item = sel[0]
        values = list(self.att_tree.item(item)["values"])
        current = values[3]
        next_status = cycle[(cycle.index(current) + 1) % len(cycle)] if current in cycle else "PRESENT"
        values[3] = next_status
        self.att_tree.item(item, values=values)

    def _save_student_attendance(self):
        att_date = self.att_date_var.get().strip()
        rows = [self.att_tree.item(i)["values"] for i in self.att_tree.get_children()]
        if not rows:
            error("No Data", "Load students first.")
            return
        conn = get_connection(); cur = conn.cursor()
        try:
            for student_id, name, roll, status in rows:
                cur.execute("""
                    INSERT INTO student_attendance (student_id, attendance_date, status, marked_by)
                    VALUES (%s,%s,%s,%s)
                    ON DUPLICATE KEY UPDATE status=VALUES(status), marked_by=VALUES(marked_by)
                """, (student_id, att_date, status, self.current_user.linked_employee_id))
            conn.commit()
            info("Saved", f"Attendance saved for {len(rows)} students on {att_date}.")
        except Exception as e:
            conn.rollback()
            error("Database Error", str(e))
        finally:
            cur.close(); conn.close()

    # ------------------------------------------------------------------ #
    # EMPLOYEE ATTENDANCE
    # ------------------------------------------------------------------ #
    def _build_employee_tab(self):
        top = ttk.Frame(self.employee_tab)
        top.pack(fill="x", padx=10, pady=10)
        ttk.Label(top, text="Date (YYYY-MM-DD):").pack(side="left")
        self.emp_att_date_var = tk.StringVar(value=str(date.today()))
        ttk.Entry(top, textvariable=self.emp_att_date_var, width=12).pack(side="left", padx=5)
        ttk.Button(top, text="Load Employees", command=self._load_employees_for_attendance).pack(side="left", padx=10)
        ttk.Button(top, text="Save Attendance", style="Accent.TButton",
                   command=self._save_employee_attendance).pack(side="left")

        cols = ("id", "name", "status")
        self.emp_att_tree, container = make_treeview(self.employee_tab, cols, height=15)
        container.pack(fill="both", expand=True, padx=10, pady=10)
        self.emp_att_tree.bind("<Double-1>", self._cycle_emp_attendance_status)
        ttk.Label(self.employee_tab,
                  text="Tip: double-click to cycle PRESENT -> ABSENT -> LATE -> ON_DUTY (work outside)",
                  foreground="#666666").pack(anchor="w", padx=10)

    def _load_employees_for_attendance(self):
        clear_tree(self.emp_att_tree)
        conn = get_connection(); cur = conn.cursor()
        cur.execute("""
            SELECT employee_id, CONCAT(first_name,' ',IFNULL(last_name,'')) FROM employees
            WHERE status='ACTIVE' ORDER BY first_name
        """)
        for eid, name in cur.fetchall():
            self.emp_att_tree.insert("", "end", values=(eid, name, "PRESENT"))
        cur.close(); conn.close()

    def _cycle_emp_attendance_status(self, event):
        sel = self.emp_att_tree.selection()
        if not sel:
            return
        cycle = ["PRESENT", "ABSENT", "LATE", "ON_DUTY"]
        item = sel[0]
        values = list(self.emp_att_tree.item(item)["values"])
        current = values[2]
        values[2] = cycle[(cycle.index(current) + 1) % len(cycle)] if current in cycle else "PRESENT"
        self.emp_att_tree.item(item, values=values)

    def _save_employee_attendance(self):
        att_date = self.emp_att_date_var.get().strip()
        rows = [self.emp_att_tree.item(i)["values"] for i in self.emp_att_tree.get_children()]
        if not rows:
            error("No Data", "Load employees first.")
            return
        conn = get_connection(); cur = conn.cursor()
        try:
            for emp_id, name, status in rows:
                cur.execute("""
                    INSERT INTO employee_attendance (employee_id, attendance_date, status)
                    VALUES (%s,%s,%s)
                    ON DUPLICATE KEY UPDATE status=VALUES(status)
                """, (emp_id, att_date, status))
            conn.commit()
            info("Saved", f"Attendance saved for {len(rows)} employees on {att_date}.")
        except Exception as e:
            conn.rollback()
            error("Database Error", str(e))
        finally:
            cur.close(); conn.close()

    # ------------------------------------------------------------------ #
    # EMPLOYEE LEAVE
    # ------------------------------------------------------------------ #
    def _build_leave_tab(self):
        form = ttk.Frame(self.leave_tab)
        form.pack(fill="x", padx=15, pady=15)

        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT employee_id, CONCAT(first_name,' ',IFNULL(last_name,'')) FROM employees")
        emp_rows = cur.fetchall()
        cur.execute("SELECT leave_type_id, type_name FROM leave_types")
        leave_type_rows = cur.fetchall()
        cur.close(); conn.close()

        self.leave_emp_map = {name: eid for eid, name in emp_rows}
        self.leave_type_map = {name: tid for tid, name in leave_type_rows}

        ttk.Label(form, text="Employee:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.leave_emp_var = tk.StringVar()
        ttk.Combobox(form, textvariable=self.leave_emp_var, values=list(self.leave_emp_map),
                     state="readonly", width=25).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(form, text="Leave Type:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.leave_type_var = tk.StringVar()
        ttk.Combobox(form, textvariable=self.leave_type_var, values=list(self.leave_type_map),
                     state="readonly", width=25).grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(form, text="From Date:").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        self.leave_from_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.leave_from_var, width=27).grid(row=2, column=1, padx=5, pady=5)

        ttk.Label(form, text="To Date:").grid(row=3, column=0, sticky="e", padx=5, pady=5)
        self.leave_to_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.leave_to_var, width=27).grid(row=3, column=1, padx=5, pady=5)

        ttk.Label(form, text="Reason:").grid(row=4, column=0, sticky="e", padx=5, pady=5)
        self.leave_reason_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.leave_reason_var, width=27).grid(row=4, column=1, padx=5, pady=5)

        ttk.Button(form, text="Apply Leave", command=self._apply_leave).grid(row=5, column=0, columnspan=2, pady=10)

        action_bar = ttk.Frame(self.leave_tab)
        action_bar.pack(fill="x", padx=15)
        ttk.Button(action_bar, text="Refresh Pending Leaves", command=self._load_leaves).pack(side="left")
        ttk.Button(action_bar, text="Approve Selected", command=lambda: self._decide_leave("APPROVED")).pack(side="left", padx=5)
        ttk.Button(action_bar, text="Reject Selected", command=lambda: self._decide_leave("REJECTED")).pack(side="left")

        cols = ("id", "employee", "type", "from", "to", "reason", "status")
        self.leave_tree, container = make_treeview(self.leave_tab, cols, height=10)
        container.pack(fill="both", expand=True, padx=15, pady=10)
        self._load_leaves()

    def _apply_leave(self):
        emp_id = self.leave_emp_map.get(self.leave_emp_var.get())
        type_id = self.leave_type_map.get(self.leave_type_var.get())
        if not emp_id or not type_id or not self.leave_from_var.get() or not self.leave_to_var.get():
            error("Missing Data", "Please fill all required fields.")
            return
        conn = get_connection(); cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO employee_leaves (employee_id, leave_type_id, from_date, to_date, reason)
                VALUES (%s,%s,%s,%s,%s)
            """, (emp_id, type_id, self.leave_from_var.get(), self.leave_to_var.get(), self.leave_reason_var.get()))
            conn.commit()
            info("Applied", "Leave application submitted.")
            self._load_leaves()
        except Exception as e:
            conn.rollback()
            error("Database Error", str(e))
        finally:
            cur.close(); conn.close()

    def _load_leaves(self):
        clear_tree(self.leave_tree)
        conn = get_connection(); cur = conn.cursor()
        cur.execute("""
            SELECT l.leave_id, CONCAT(e.first_name,' ',IFNULL(e.last_name,'')), lt.type_name,
                   l.from_date, l.to_date, l.reason, l.status
            FROM employee_leaves l
            JOIN employees e ON e.employee_id = l.employee_id
            JOIN leave_types lt ON lt.leave_type_id = l.leave_type_id
            ORDER BY l.applied_on DESC
        """)
        for row in cur.fetchall():
            self.leave_tree.insert("", "end", values=row)
        cur.close(); conn.close()

    def _decide_leave(self, decision):
        sel = self.leave_tree.selection()
        if not sel:
            error("No Selection", "Please select a leave record.")
            return
        leave_id = self.leave_tree.item(sel[0])["values"][0]
        conn = get_connection(); cur = conn.cursor()
        cur.execute("UPDATE employee_leaves SET status=%s, approved_by=%s WHERE leave_id=%s",
                    (decision, self.current_user.linked_employee_id, leave_id))
        conn.commit(); cur.close(); conn.close()
        self._load_leaves()

    # ------------------------------------------------------------------ #
    # ABSENTEE NOTIFICATION SIMULATOR
    # ------------------------------------------------------------------ #
    def _build_notify_tab(self):
        top = ttk.Frame(self.notify_tab)
        top.pack(fill="x", padx=15, pady=15)
        ttk.Label(top, text="Date to check (YYYY-MM-DD):").pack(side="left")
        self.notify_date_var = tk.StringVar(value=str(date.today()))
        ttk.Entry(top, textvariable=self.notify_date_var, width=15).pack(side="left", padx=5)
        ttk.Button(top, text="Simulate Send Notifications", style="Accent.TButton",
                   command=self._simulate_notifications).pack(side="left", padx=10)

        self.notify_log_box = tk.Text(self.notify_tab, height=20, bg="#0f172a", fg="#4ade80",
                                       font=("Consolas", 9))
        self.notify_log_box.pack(fill="both", expand=True, padx=15, pady=10)

    def _simulate_notifications(self):
        check_date = self.notify_date_var.get().strip()
        conn = get_connection(); cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT s.student_id, CONCAT(s.first_name,' ',IFNULL(s.last_name,'')) AS name,
                   s.guardian_email, s.guardian_phone, s.email, s.phone, s.father_name
            FROM student_attendance sa
            JOIN students s ON s.student_id = sa.student_id
            WHERE sa.attendance_date = %s AND sa.status = 'ABSENT'
        """, (check_date,))
        absentees = cur.fetchall()

        self.notify_log_box.delete("1.0", "end")
        if not absentees:
            self.notify_log_box.insert("end", f"No absentees recorded for {check_date}.\n")
            cur.close(); conn.close()
            return

        count = 0
        for stu in absentees:
            email = stu["guardian_email"] or stu["email"] or "no-email-on-file@example.com"
            phone = stu["guardian_phone"] or stu["phone"] or "N/A"
            message = (f"Dear Parent/Guardian of {stu['name']}, this is to inform you that your "
                       f"ward was marked ABSENT on {check_date}. - School Administration")

            for channel, target in (("EMAIL", email), ("SMS", phone)):
                cur.execute("""
                    INSERT INTO notification_log
                        (recipient_type, recipient_ref_id, channel, subject, message_body, related_date)
                    VALUES ('STUDENT_GUARDIAN', %s, %s, %s, %s, %s)
                """, (stu["student_id"], channel, "Absence Alert", message, check_date))
                self.notify_log_box.insert("end", f"[SIMULATED {channel}] -> {target} : {message}\n")
                count += 1
        conn.commit()
        cur.close(); conn.close()
        self.notify_log_box.insert("end", f"\n{count} simulated notifications logged to notification_log.\n")