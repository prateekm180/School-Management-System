"""
===============================================================================
 reports.py
-------------------------------------------------------------------------------
 A single, DATA-DRIVEN reporting engine.

 Design rationale (why this scales to 40+ reports without 40+ screens):
   Every report is just an entry in the REPORTS dictionary below:
       "Report Display Name": (sql_query, column_headers)
   The GUI simply lists the dictionary keys in a listbox; picking one runs
   its SQL and renders the result in a generic Treeview. Adding report #41
   to this system for a real deployment means adding ONE dictionary entry --
   no new screens, no new plumbing.

 This file ships with a representative set of reports across every module
 (attendance, exams, finance, library, HR) to demonstrate the pattern;
 the same technique extends to the full 40+ report checklist.
===============================================================================
"""

import tkinter as tk
from tkinter import ttk

from db_config import get_connection
from utils import make_treeview, clear_tree, error

# ---------------------------------------------------------------------------
# REPORT CATALOG: name -> (SQL, [column headers])
# Add new reports here -- the UI below needs no changes.
# ---------------------------------------------------------------------------
REPORTS = {

    "Fee Defaulters (Unpaid/Overdue Invoices)": ("""
        SELECT s.admission_no, CONCAT(s.first_name,' ',IFNULL(s.last_name,'')) AS name,
               c.class_name, i.total_amount, i.due_date, i.status
        FROM student_invoices i
        JOIN students s ON s.student_id = i.student_id
        JOIN classes c ON c.class_id = s.class_id
        WHERE i.status IN ('UNPAID','PARTIALLY_PAID','OVERDUE')
        ORDER BY i.due_date
    """, ["Admission No", "Name", "Class", "Amount Due", "Due Date", "Status"]),

    "Low Attendance Flags (< 75%)": ("""
        SELECT s.admission_no, CONCAT(s.first_name,' ',IFNULL(s.last_name,'')) AS name,
               c.class_name,
               ROUND(100 * SUM(CASE WHEN sa.status='PRESENT' THEN 1 ELSE 0 END) / COUNT(*), 2) AS attendance_pct,
               COUNT(*) AS days_recorded
        FROM student_attendance sa
        JOIN students s ON s.student_id = sa.student_id
        JOIN classes c ON c.class_id = s.class_id
        GROUP BY s.student_id
        HAVING attendance_pct < 75
        ORDER BY attendance_pct
    """, ["Admission No", "Name", "Class", "Attendance %", "Days Recorded"]),

    "Class-wise Average Performance": ("""
        SELECT c.class_name, sub.subject_name,
               ROUND(AVG(m.marks_obtained), 2) AS avg_marks,
               ROUND(100 * AVG(m.marks_obtained / es.max_marks), 2) AS avg_pct
        FROM student_marks m
        JOIN exam_schedule es ON es.schedule_id = m.schedule_id
        JOIN classes c ON c.class_id = es.class_id
        JOIN subjects sub ON sub.subject_id = es.subject_id
        GROUP BY c.class_id, sub.subject_id
        ORDER BY c.class_order, sub.subject_name
    """, ["Class", "Subject", "Avg Marks", "Avg %"]),

    "Library Overdue Books": ("""
        SELECT b.title, bi.borrower_type, bi.borrower_ref_id, bi.issue_date, bi.due_date,
               DATEDIFF(CURDATE(), bi.due_date) AS days_overdue
        FROM book_issues bi
        JOIN books b ON b.book_id = bi.book_id
        WHERE bi.status='ISSUED' AND bi.due_date < CURDATE()
        ORDER BY days_overdue DESC
    """, ["Title", "Borrower Type", "Borrower ID", "Issue Date", "Due Date", "Days Overdue"]),

    "Budget Balance Sheet (Income vs Expense by Head)": ("""
        SELECT h.head_type, h.head_name, ROUND(SUM(t.amount), 2) AS total
        FROM budget_transactions t
        JOIN account_heads h ON h.head_id = t.head_id
        GROUP BY h.head_id
        ORDER BY h.head_type, total DESC
    """, ["Type", "Head", "Total Amount"]),

    "Student Directory by Class": ("""
        SELECT c.class_name, sec.section_name, s.roll_no,
               CONCAT(s.first_name,' ',IFNULL(s.last_name,'')) AS name, s.status
        FROM students s
        JOIN classes c ON c.class_id = s.class_id
        JOIN sections sec ON sec.section_id = s.section_id
        ORDER BY c.class_order, sec.section_name, s.roll_no
    """, ["Class", "Section", "Roll No", "Name", "Status"]),

    "Employee Directory": ("""
        SELECT e.employee_code, CONCAT(e.first_name,' ',IFNULL(e.last_name,'')) AS name,
               d.title, e.employee_type, e.status
        FROM employees e JOIN designations d ON d.designation_id = e.designation_id
        ORDER BY e.employee_type, name
    """, ["Code", "Name", "Designation", "Type", "Status"]),

    "Employee Leave Summary (Approved Days Taken)": ("""
        SELECT CONCAT(e.first_name,' ',IFNULL(e.last_name,'')) AS name, lt.type_name,
               SUM(DATEDIFF(l.to_date, l.from_date) + 1) AS days_taken
        FROM employee_leaves l
        JOIN employees e ON e.employee_id = l.employee_id
        JOIN leave_types lt ON lt.leave_type_id = l.leave_type_id
        WHERE l.status = 'APPROVED'
        GROUP BY e.employee_id, lt.leave_type_id
        ORDER BY name
    """, ["Employee", "Leave Type", "Days Taken"]),

    "Daily Employee Attendance Snapshot (Today)": ("""
        SELECT CONCAT(e.first_name,' ',IFNULL(e.last_name,'')) AS name, ea.status, ea.check_in, ea.check_out
        FROM employee_attendance ea
        JOIN employees e ON e.employee_id = ea.employee_id
        WHERE ea.attendance_date = CURDATE()
        ORDER BY ea.status
    """, ["Employee", "Status", "Check In", "Check Out"]),

    "Fee Collection Summary (Payment Mode-wise)": ("""
        SELECT payment_mode, COUNT(*) AS num_payments, ROUND(SUM(amount_paid),2) AS total_collected
        FROM fee_payments
        GROUP BY payment_mode
        ORDER BY total_collected DESC
    """, ["Payment Mode", "No. of Payments", "Total Collected"]),

    "Subject-wise Pass/Fail Count (Latest Exam)": ("""
        SELECT sub.subject_name,
               SUM(CASE WHEN m.marks_obtained >= es.min_pass_marks THEN 1 ELSE 0 END) AS passed,
               SUM(CASE WHEN m.marks_obtained < es.min_pass_marks THEN 1 ELSE 0 END) AS failed
        FROM student_marks m
        JOIN exam_schedule es ON es.schedule_id = m.schedule_id
        JOIN subjects sub ON sub.subject_id = es.subject_id
        WHERE es.exam_id = (SELECT MAX(exam_id) FROM exams)
        GROUP BY sub.subject_id
    """, ["Subject", "Passed", "Failed"]),

    "Hostel Room Occupancy": ("""
        SELECT hr.hostel_name, hr.room_no, hr.capacity,
               COUNT(ha.allocation_id) AS occupied,
               (hr.capacity - COUNT(ha.allocation_id)) AS vacant
        FROM hostel_rooms hr
        LEFT JOIN hostel_allocations ha ON ha.room_id = hr.room_id AND ha.status='ACTIVE'
        GROUP BY hr.room_id
    """, ["Hostel", "Room No", "Capacity", "Occupied", "Vacant"]),

    "Admissions This Year (by Mode)": ("""
        SELECT admission_mode, COUNT(*) AS total
        FROM students
        WHERE academic_year_id = (SELECT academic_year_id FROM academic_years WHERE is_current=TRUE)
        GROUP BY admission_mode
    """, ["Admission Mode", "Total"]),
}


class ReportsModuleFrame(ttk.Frame):
    """
    Two-pane layout:
      Left  : scrollable list of available report names (extensible catalog)
      Right : Treeview showing the result set of the selected report
    """
    def __init__(self, parent, current_user):
        super().__init__(parent)
        self.current_user = current_user

        ttk.Label(self, text=f"Reporting Engine  ({len(REPORTS)} reports available -- "
                              f"extensible to 40+ by adding catalog entries)",
                  style="SubHeader.TLabel").pack(anchor="w", padx=15, pady=10)

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        left = ttk.Frame(body)
        left.pack(side="left", fill="y", padx=(0, 10))

        self.report_listbox = tk.Listbox(left, width=42, height=25, font=("Segoe UI", 9))
        for name in REPORTS:
            self.report_listbox.insert("end", name)
        self.report_listbox.pack(fill="y", expand=True)
        self.report_listbox.bind("<<ListboxSelect>>", self._run_selected_report)

        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True)

        self.result_label = ttk.Label(right, text="Select a report from the list to run it.")
        self.result_label.pack(anchor="w", pady=(0, 5))

        self.result_tree = None
        self.result_container_holder = right  # where we mount the Treeview dynamically

    def _run_selected_report(self, event=None):
        selection = self.report_listbox.curselection()
        if not selection:
            return
        report_name = self.report_listbox.get(selection[0])
        sql, headers = REPORTS[report_name]

        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute(sql)
            rows = cur.fetchall()
        except Exception as e:
            error("Report Error", str(e))
            cur.close(); conn.close()
            return
        cur.close(); conn.close()

        # Rebuild the Treeview with columns matching this specific report
        if self.result_tree is not None:
            self.result_tree.master.destroy()

        cols = [f"c{i}" for i in range(len(headers))]
        headings = {f"c{i}": h for i, h in enumerate(headers)}
        self.result_tree, container = make_treeview(self.result_container_holder, cols, headings, height=22)
        container.pack(fill="both", expand=True)

        for row in rows:
            self.result_tree.insert("", "end", values=row)

        self.result_label.config(text=f"{report_name}  --  {len(rows)} row(s)")