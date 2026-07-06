"""
===============================================================================
 employee.py
-------------------------------------------------------------------------------
 Employee/Staff Management:
   - Add employees (teaching / admin / support) with designation & department
   - Directory listing with filter by employee_type
   - Teacher <-> Class/Section/Subject mapping viewer
===============================================================================
"""

import tkinter as tk
from tkinter import ttk
from datetime import date

from db_config import get_connection
from utils import make_treeview, clear_tree, build_form, get_value, info, error


def fetch_lookup(table, id_col, name_col):
    conn = get_connection(); cur = conn.cursor()
    cur.execute(f"SELECT {id_col}, {name_col} FROM {table} ORDER BY {name_col}")
    rows = cur.fetchall(); cur.close(); conn.close()
    return rows


class EmployeeModuleFrame(ttk.Frame):
    def __init__(self, parent, current_user):
        super().__init__(parent)
        self.current_user = current_user

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.directory_tab = ttk.Frame(notebook)
        self.add_tab = ttk.Frame(notebook)
        self.mapping_tab = ttk.Frame(notebook)

        notebook.add(self.directory_tab, text="Staff Directory")
        notebook.add(self.add_tab, text="Add Employee")
        notebook.add(self.mapping_tab, text="Teacher-Subject Mapping")

        self._build_directory_tab()
        self._build_add_tab()
        self._build_mapping_tab()

    # ---------------------------------------------------------------- #
    def _build_directory_tab(self):
        top = ttk.Frame(self.directory_tab)
        top.pack(fill="x", padx=10, pady=10)
        ttk.Label(top, text="Filter by type:").pack(side="left")
        self.type_filter = ttk.Combobox(top, values=["ALL", "TEACHING", "ADMIN", "SUPPORT"],
                                         state="readonly", width=15)
        self.type_filter.set("ALL")
        self.type_filter.pack(side="left", padx=5)
        ttk.Button(top, text="Refresh", command=self._load_employees).pack(side="left")

        cols = ("code", "name", "designation", "department", "type", "phone", "status")
        widths = {"code": 80, "name": 150, "designation": 100, "department": 110,
                  "type": 90, "phone": 100, "status": 80}
        self.emp_tree, container = make_treeview(self.directory_tab, cols, widths=widths)
        container.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self._load_employees()

    def _load_employees(self):
        clear_tree(self.emp_tree)
        conn = get_connection(); cur = conn.cursor()
        filt = self.type_filter.get()
        query = """
            SELECT e.employee_code, CONCAT(e.first_name,' ',IFNULL(e.last_name,'')),
                   d.title, dep.department_name, e.employee_type, e.phone, e.status
            FROM employees e
            JOIN designations d ON d.designation_id = e.designation_id
            LEFT JOIN departments dep ON dep.department_id = e.department_id
        """
        params = ()
        if filt and filt != "ALL":
            query += " WHERE e.employee_type = %s"
            params = (filt,)
        cur.execute(query, params)
        for row in cur.fetchall():
            self.emp_tree.insert("", "end", values=row)
        cur.close(); conn.close()

    # ---------------------------------------------------------------- #
    def _build_add_tab(self):
        ttk.Label(self.add_tab, text="Add New Employee", style="SubHeader.TLabel").pack(anchor="w", padx=15, pady=10)
        form = ttk.Frame(self.add_tab)
        form.pack(anchor="w", padx=15)

        designations = fetch_lookup("designations", "designation_id", "title")
        departments = fetch_lookup("departments", "department_id", "department_name")
        self.designation_map = {d[1]: d[0] for d in designations}
        self.department_map = {d[1]: d[0] for d in departments}

        fields = [
            ("code", "Employee Code", "entry"),
            ("first_name", "First Name", "entry"),
            ("last_name", "Last Name", "entry"),
            ("dob", "Date of Birth (YYYY-MM-DD)", "entry"),
            ("gender", "Gender", "combo:MALE,FEMALE,OTHER"),
            ("designation", "Designation", "combo:" + ",".join(self.designation_map)),
            ("department", "Department", "combo:" + ",".join(self.department_map)),
            ("emp_type", "Employee Type", "combo:TEACHING,ADMIN,SUPPORT"),
            ("phone", "Phone", "entry"),
            ("email", "Email", "entry"),
            ("doj", "Date of Joining (YYYY-MM-DD)", "entry"),
        ]
        self.emp_widgets = build_form(form, fields)
        ttk.Button(self.add_tab, text="Save Employee", style="Accent.TButton",
                   command=self._save_employee).pack(pady=15)

    def _save_employee(self):
        d = {k: get_value(w) for k, w in self.emp_widgets.items()}
        if not d["code"] or not d["first_name"] or not d["doj"]:
            error("Missing Data", "Employee code, first name and date of joining are required.")
            return
        conn = get_connection(); cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO employees
                    (employee_code, first_name, last_name, dob, gender, designation_id,
                     department_id, employee_type, phone, email, date_of_joining)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (d["code"], d["first_name"], d["last_name"], d["dob"] or None, d["gender"],
                  self.designation_map.get(d["designation"]), self.department_map.get(d["department"]),
                  d["emp_type"], d["phone"], d["email"], d["doj"]))
            conn.commit()
            info("Saved", f"Employee {d['first_name']} added successfully.")
            self._load_employees()
        except Exception as e:
            conn.rollback()
            error("Database Error", str(e))
        finally:
            cur.close(); conn.close()

    # ---------------------------------------------------------------- #
    def _build_mapping_tab(self):
        cols = ("teacher", "class", "section", "subject", "class_teacher")
        self.map_tree, container = make_treeview(self.mapping_tab, cols, height=15)
        container.pack(fill="both", expand=True, padx=10, pady=10)
        ttk.Button(self.mapping_tab, text="Refresh", command=self._load_mapping).pack(pady=5)
        self._load_mapping()

    def _load_mapping(self):
        clear_tree(self.map_tree)
        conn = get_connection(); cur = conn.cursor()
        cur.execute("""
            SELECT CONCAT(e.first_name,' ',IFNULL(e.last_name,'')), c.class_name, sec.section_name,
                   sub.subject_name, IF(m.is_class_teacher,'Yes','No')
            FROM teacher_subject_mapping m
            JOIN employees e ON e.employee_id = m.employee_id
            JOIN classes c ON c.class_id = m.class_id
            JOIN sections sec ON sec.section_id = m.section_id
            JOIN subjects sub ON sub.subject_id = m.subject_id
            ORDER BY c.class_order, sec.section_name
        """)
        for row in cur.fetchall():
            self.map_tree.insert("", "end", values=row)
        cur.close(); conn.close()