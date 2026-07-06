"""
===============================================================================
 library.py
-------------------------------------------------------------------------------
 Covers:
   - Book catalog (add/list, tracks total vs available copies)
   - Book Issue to a student or employee
   - Book Return with automatic fine calculation (Rs.2/day beyond due date)
===============================================================================
"""

import tkinter as tk
from tkinter import ttk
from datetime import date, timedelta

from db_config import get_connection
from utils import make_treeview, clear_tree, info, error

FINE_PER_DAY = 2.0
DEFAULT_LOAN_DAYS = 14


class LibraryModuleFrame(ttk.Frame):
    def __init__(self, parent, current_user):
        super().__init__(parent)
        self.current_user = current_user

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.catalog_tab = ttk.Frame(notebook)
        self.issue_tab = ttk.Frame(notebook)
        self.return_tab = ttk.Frame(notebook)

        notebook.add(self.catalog_tab, text="Book Catalog")
        notebook.add(self.issue_tab, text="Issue Book")
        notebook.add(self.return_tab, text="Return Book / Fines")

        self._build_catalog_tab()
        self._build_issue_tab()
        self._build_return_tab()

    # ------------------------------------------------------------------ #
    # CATALOG
    # ------------------------------------------------------------------ #
    def _build_catalog_tab(self):
        form = ttk.Frame(self.catalog_tab)
        form.pack(fill="x", padx=15, pady=15)

        labels = ["ISBN", "Title", "Author", "Publisher", "Category", "Total Copies", "Rack No"]
        self.book_vars = {}
        for i, lbl in enumerate(labels):
            ttk.Label(form, text=lbl + ":").grid(row=i // 2, column=(i % 2) * 2, sticky="e", padx=5, pady=5)
            var = tk.StringVar()
            ttk.Entry(form, textvariable=var, width=22).grid(row=i // 2, column=(i % 2) * 2 + 1, padx=5, pady=5)
            self.book_vars[lbl] = var

        ttk.Button(form, text="Add Book", style="Accent.TButton", command=self._add_book).grid(
            row=4, column=0, columnspan=2, pady=10)

        cols = ("isbn", "title", "author", "category", "total", "available", "rack")
        self.book_tree, container = make_treeview(self.catalog_tab, cols, height=12)
        container.pack(fill="both", expand=True, padx=15, pady=10)
        self._load_books()

    def _add_book(self):
        v = {k: var.get().strip() for k, var in self.book_vars.items()}
        if not v["Title"]:
            error("Missing Data", "Title is required.")
            return
        try:
            total = int(v["Total Copies"] or 1)
        except ValueError:
            error("Invalid Input", "Total copies must be a whole number.")
            return
        conn = get_connection(); cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO books (isbn, title, author, publisher, category, total_copies, available_copies, rack_no)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """, (v["ISBN"] or None, v["Title"], v["Author"], v["Publisher"], v["Category"], total, total, v["Rack No"]))
            conn.commit()
            info("Added", f"Book '{v['Title']}' added with {total} copies.")
            self._load_books()
        except Exception as e:
            conn.rollback()
            error("Database Error", str(e))
        finally:
            cur.close(); conn.close()

    def _load_books(self):
        clear_tree(self.book_tree)
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT isbn, title, author, category, total_copies, available_copies, rack_no FROM books")
        for row in cur.fetchall():
            self.book_tree.insert("", "end", values=row)
        cur.close(); conn.close()

    # ------------------------------------------------------------------ #
    # ISSUE
    # ------------------------------------------------------------------ #
    def _build_issue_tab(self):
        form = ttk.Frame(self.issue_tab)
        form.pack(fill="x", padx=15, pady=15)

        ttk.Label(form, text="Book ISBN or Title:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.issue_book_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.issue_book_var, width=25).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(form, text="Borrower Type:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.borrower_type_var = tk.StringVar(value="STUDENT")
        ttk.Combobox(form, textvariable=self.borrower_type_var, values=["STUDENT", "EMPLOYEE"],
                     state="readonly", width=15).grid(row=1, column=1, sticky="w", padx=5, pady=5)

        ttk.Label(form, text="Borrower ID (student_id / employee_id):").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        self.borrower_id_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.borrower_id_var, width=25).grid(row=2, column=1, padx=5, pady=5)
        ttk.Label(form, text="(Tip: find IDs via the Student/Staff Directory)",
                  foreground="#777777").grid(row=3, column=1, sticky="w")

        ttk.Button(form, text="Issue Book", style="Accent.TButton", command=self._issue_book).grid(
            row=4, column=0, columnspan=2, pady=10)

    def _issue_book(self):
        book_ref = self.issue_book_var.get().strip()
        borrower_type = self.borrower_type_var.get()
        borrower_id = self.borrower_id_var.get().strip()

        if not book_ref or not borrower_id:
            error("Missing Data", "Enter the book and borrower ID.")
            return

        conn = get_connection(); cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM books WHERE isbn=%s OR title=%s", (book_ref, book_ref))
        book = cur.fetchone()
        if not book:
            error("Not Found", "Book not found by that ISBN/title.")
            cur.close(); conn.close()
            return
        if book["available_copies"] <= 0:
            error("Unavailable", "No available copies of this book right now.")
            cur.close(); conn.close()
            return

        issue_date = date.today()
        due_date = issue_date + timedelta(days=DEFAULT_LOAN_DAYS)
        try:
            cur.execute("""
                INSERT INTO book_issues (book_id, borrower_type, borrower_ref_id, issue_date, due_date, status)
                VALUES (%s,%s,%s,%s,%s,'ISSUED')
            """, (book["book_id"], borrower_type, borrower_id, issue_date, due_date))
            cur.execute("UPDATE books SET available_copies = available_copies - 1 WHERE book_id=%s",
                        (book["book_id"],))
            conn.commit()
            info("Issued", f"'{book['title']}' issued. Due back on {due_date}.")
            self._load_books()
        except Exception as e:
            conn.rollback()
            error("Database Error", str(e))
        finally:
            cur.close(); conn.close()

    # ------------------------------------------------------------------ #
    # RETURN + FINES
    # ------------------------------------------------------------------ #
    def _build_return_tab(self):
        top = ttk.Frame(self.return_tab)
        top.pack(fill="x", padx=15, pady=15)
        ttk.Button(top, text="Refresh Currently Issued Books", command=self._load_issued).pack(side="left")
        ttk.Button(top, text="Return Selected", style="Accent.TButton",
                   command=self._return_book).pack(side="left", padx=10)

        cols = ("issue_id", "book", "borrower_type", "borrower_id", "issue_date", "due_date", "days_overdue")
        self.issue_tree, container = make_treeview(self.return_tab, cols, height=15)
        container.pack(fill="both", expand=True, padx=15, pady=10)
        self._load_issued()

    def _load_issued(self):
        clear_tree(self.issue_tree)
        conn = get_connection(); cur = conn.cursor()
        cur.execute("""
            SELECT bi.issue_id, b.title, bi.borrower_type, bi.borrower_ref_id, bi.issue_date, bi.due_date,
                   GREATEST(DATEDIFF(CURDATE(), bi.due_date), 0) AS overdue
            FROM book_issues bi JOIN books b ON b.book_id = bi.book_id
            WHERE bi.status = 'ISSUED'
            ORDER BY bi.due_date
        """)
        for row in cur.fetchall():
            self.issue_tree.insert("", "end", values=row)
        cur.close(); conn.close()

    def _return_book(self):
        sel = self.issue_tree.selection()
        if not sel:
            error("No Selection", "Select an issued book first.")
            return
        values = self.issue_tree.item(sel[0])["values"]
        issue_id, title, btype, bref, issue_date, due_date, overdue_days = values

        fine = round(float(overdue_days) * FINE_PER_DAY, 2)
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT book_id FROM book_issues WHERE issue_id=%s", (issue_id,))
        book_id = cur.fetchone()[0]
        try:
            cur.execute("""
                UPDATE book_issues SET return_date=%s, fine_amount=%s, status='RETURNED' WHERE issue_id=%s
            """, (date.today(), fine, issue_id))
            cur.execute("UPDATE books SET available_copies = available_copies + 1 WHERE book_id=%s", (book_id,))
            conn.commit()
            msg = f"'{title}' returned."
            if fine > 0:
                msg += f"\nOverdue by {overdue_days} day(s). Fine due: Rs.{fine:.2f}"
            info("Returned", msg)
            self._load_issued()
        except Exception as e:
            conn.rollback()
            error("Database Error", str(e))
        finally:
            cur.close(); conn.close()