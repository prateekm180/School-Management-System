"""
===============================================================================
 main.py  -- APPLICATION ENTRY POINT
-------------------------------------------------------------------------------
 Run this file to start the School Management System GUI:
     python main.py

 Flow:
   1. Shows LoginFrame (auth.py).
   2. On successful login, builds the MainDashboard:
        - A header bar with institute name + logged-in user + Logout.
        - A left sidebar whose buttons are filtered by the user's ROLE:
              ADMIN      -> sees every module
              TEACHER    -> Attendance, Exams, Student Directory (read use)
              ACCOUNTANT -> Finance
              LIBRARIAN  -> Library
              STUDENT / PARENT -> a simplified read-only "My Dashboard"
        - A content area on the right that swaps between module frames.
   3. Each module (student.py, employee.py, attendance.py, exams.py,
      finance.py, library.py, reports.py) is a self-contained ttk.Frame
      that main.py simply instantiates and shows/hides.
===============================================================================
"""

import tkinter as tk
from tkinter import ttk

from db_config import get_connection
from utils import apply_theme, COLORS, make_treeview, clear_tree
from auth import LoginFrame

from student import StudentModuleFrame
from employee import EmployeeModuleFrame
from attendance import AttendanceModuleFrame
from exams import ExamModuleFrame
from finance import FinanceModuleFrame
from library import LibraryModuleFrame
from reports import ReportsModuleFrame


APP_TITLE = "School Management System"

# Each entry: (label, frame_class, allowed_role_names)
# ADMIN is always allowed everywhere regardless of this list.
MODULE_REGISTRY = [
    ("Student Management", StudentModuleFrame, {"TEACHER"}),
    ("Employee / Staff", EmployeeModuleFrame, set()),
    ("Attendance & Leave", AttendanceModuleFrame, {"TEACHER"}),
    ("Examinations", ExamModuleFrame, {"TEACHER"}),
    ("Finance & Fees", FinanceModuleFrame, {"ACCOUNTANT"}),
    ("Library", LibraryModuleFrame, {"LIBRARIAN"}),
    ("Reports", ReportsModuleFrame, {"TEACHER", "ACCOUNTANT", "LIBRARIAN"}),
]


class SchoolApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1180x720")
        self.minsize(1000, 640)
        apply_theme(self)

        self.current_user = None
        self.container = ttk.Frame(self)
        self.container.pack(fill="both", expand=True)

        self._show_login()

    # ------------------------------------------------------------------ #
    def _clear_container(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def _show_login(self):
        self._clear_container()
        login_frame = LoginFrame(self.container, on_success=self._on_login_success)
        login_frame.pack(fill="both", expand=True)

    def _on_login_success(self, user):
        self.current_user = user
        self._build_dashboard()

    def _logout(self):
        self.current_user = None
        self._show_login()

    # ------------------------------------------------------------------ #
    def _build_dashboard(self):
        self._clear_container()

        # ---- Header bar ------------------------------------------------
        header = tk.Frame(self.container, bg=COLORS["primary"], height=60)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(header, text=APP_TITLE, bg=COLORS["primary"], fg="white",
                 font=("Segoe UI", 14, "bold")).pack(side="left", padx=20)

        user_info = tk.Label(header, bg=COLORS["primary"], fg="white",
                              text=f"{self.current_user.full_name}  |  {self.current_user.role_name}",
                              font=("Segoe UI", 10))
        user_info.pack(side="right", padx=10)
        tk.Button(header, text="Logout", command=self._logout, bg="#C62828", fg="white",
                  relief="flat", padx=10).pack(side="right", padx=10)

        # ---- Body: sidebar + content ------------------------------------
        body = ttk.Frame(self.container)
        body.pack(fill="both", expand=True)

        sidebar = tk.Frame(body, bg=COLORS["primary"], width=220)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        self.content_area = ttk.Frame(body)
        self.content_area.pack(side="left", fill="both", expand=True)

        role = self.current_user.role_name

        if role in ("STUDENT", "PARENT"):
            self._build_sidebar_button(sidebar, "My Dashboard", self._show_student_dashboard, first=True)
            self._show_student_dashboard()
            return

        # Staff-side roles get the full module sidebar (filtered by role)
        self._build_sidebar_button(sidebar, "Home", self._show_home, first=True)
        for label, frame_cls, allowed_roles in MODULE_REGISTRY:
            if role == "ADMIN" or role in allowed_roles:
                self._build_sidebar_button(sidebar, label, lambda fc=frame_cls: self._show_module(fc))

        self._show_home()

    def _build_sidebar_button(self, sidebar, label, command, first=False):
        btn = tk.Button(sidebar, text=label, command=command, bg=COLORS["primary"], fg="white",
                         activebackground=COLORS["accent"], activeforeground="white",
                         relief="flat", anchor="w", padx=20, pady=12, font=("Segoe UI", 10),
                         bd=0, highlightthickness=0)
        btn.pack(fill="x", pady=(2 if first else 0))

    # ------------------------------------------------------------------ #
    def _clear_content(self):
        for widget in self.content_area.winfo_children():
            widget.destroy()

    def _show_module(self, frame_cls):
        self._clear_content()
        frame = frame_cls(self.content_area, self.current_user)
        frame.pack(fill="both", expand=True)

    # ------------------------------------------------------------------ #
    # HOME / ADMIN SUMMARY DASHBOARD
    # ------------------------------------------------------------------ #
    def _show_home(self):
        self._clear_content()
        wrapper = ttk.Frame(self.content_area)
        wrapper.pack(fill="both", expand=True, padx=25, pady=25)

        ttk.Label(wrapper, text=f"Welcome, {self.current_user.full_name}",
                  style="SubHeader.TLabel").pack(anchor="w", pady=(0, 15))

        stats = self._fetch_quick_stats()
        cards = ttk.Frame(wrapper)
        cards.pack(fill="x", pady=10)
        for i, (label, value) in enumerate(stats):
            card = tk.Frame(cards, bg="white", bd=1, relief="solid", padx=20, pady=15)
            card.grid(row=0, column=i, padx=10, sticky="nsew")
            tk.Label(card, text=str(value), font=("Segoe UI", 20, "bold"),
                     bg="white", fg=COLORS["primary"]).pack()
            tk.Label(card, text=label, font=("Segoe UI", 9), bg="white", fg="#555").pack()
        for i in range(len(stats)):
            cards.columnconfigure(i, weight=1)

        ttk.Label(wrapper, text="Use the left-hand menu to access each module.",
                  foreground="#666666").pack(anchor="w", pady=(20, 0))

    def _fetch_quick_stats(self):
        conn = get_connection(); cur = conn.cursor()
        stats = []
        try:
            cur.execute("SELECT COUNT(*) FROM students WHERE status='ACTIVE'")
            stats.append(("Active Students", cur.fetchone()[0]))
            cur.execute("SELECT COUNT(*) FROM employees WHERE status='ACTIVE'")
            stats.append(("Active Staff", cur.fetchone()[0]))
            cur.execute("SELECT COUNT(*) FROM student_invoices WHERE status IN ('UNPAID','PARTIALLY_PAID','OVERDUE')")
            stats.append(("Unpaid Invoices", cur.fetchone()[0]))
            cur.execute("SELECT COUNT(*) FROM book_issues WHERE status='ISSUED'")
            stats.append(("Books Issued", cur.fetchone()[0]))
        finally:
            cur.close(); conn.close()
        return stats

    # ------------------------------------------------------------------ #
    # STUDENT / PARENT READ-ONLY DASHBOARD
    # ------------------------------------------------------------------ #
    def _show_student_dashboard(self):
        self._clear_content()
        student_id = self.current_user.linked_student_id
        wrapper = ttk.Frame(self.content_area)
        wrapper.pack(fill="both", expand=True, padx=25, pady=25)

        if not student_id:
            ttk.Label(wrapper, text="No student profile is linked to this account.").pack()
            return

        conn = get_connection(); cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT s.*, c.class_name, sec.section_name FROM students s
            JOIN classes c ON c.class_id = s.class_id
            JOIN sections sec ON sec.section_id = s.section_id
            WHERE s.student_id = %s
        """, (student_id,))
        stu = cur.fetchone()

        ttk.Label(wrapper, text=f"{stu['first_name']} {stu['last_name'] or ''}  --  "
                                 f"{stu['class_name']} {stu['section_name']}",
                  style="SubHeader.TLabel").pack(anchor="w", pady=(0, 15))

        # Attendance %
        cur.execute("""
            SELECT ROUND(100*SUM(status='PRESENT')/COUNT(*),2) FROM student_attendance WHERE student_id=%s
        """, (student_id,))
        att_row = cur.fetchone()
        att_pct = list(att_row.values())[0] if att_row and list(att_row.values())[0] is not None else "N/A"

        # Pending fees
        cur.execute("""
            SELECT IFNULL(SUM(total_amount),0) FROM student_invoices
            WHERE student_id=%s AND status IN ('UNPAID','PARTIALLY_PAID','OVERDUE')
        """, (student_id,))
        pending_fees = list(cur.fetchone().values())[0]

        cards = ttk.Frame(wrapper)
        cards.pack(fill="x", pady=10)
        for i, (label, value) in enumerate([("Attendance %", att_pct), ("Pending Fees (Rs.)", pending_fees)]):
            card = tk.Frame(cards, bg="white", bd=1, relief="solid", padx=20, pady=15)
            card.grid(row=0, column=i, padx=10, sticky="nsew")
            tk.Label(card, text=str(value), font=("Segoe UI", 20, "bold"),
                     bg="white", fg=COLORS["primary"]).pack()
            tk.Label(card, text=label, font=("Segoe UI", 9), bg="white", fg="#555").pack()

        ttk.Label(wrapper, text="Recent Marks", style="SubHeader.TLabel").pack(anchor="w", pady=(25, 5))
        cols = ("exam", "subject", "marks", "max")
        tree, container = make_treeview(wrapper, cols, height=8)
        container.pack(fill="both", expand=True)

        cur.execute("""
            SELECT ex.exam_name, sub.subject_name, m.marks_obtained, es.max_marks
            FROM student_marks m
            JOIN exam_schedule es ON es.schedule_id = m.schedule_id
            JOIN exams ex ON ex.exam_id = es.exam_id
            JOIN subjects sub ON sub.subject_id = es.subject_id
            WHERE m.student_id = %s
            ORDER BY ex.exam_id DESC
        """, (student_id,))
        for row in cur.fetchall():
            tree.insert("", "end", values=(row["exam_name"], row["subject_name"],
                                            row["marks_obtained"], row["max_marks"]))
        cur.close(); conn.close()


if __name__ == "__main__":
    app = SchoolApp()
    app.mainloop()