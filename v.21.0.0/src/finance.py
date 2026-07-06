"""
===============================================================================
 finance.py
-------------------------------------------------------------------------------
 Covers:
   - Accounts & Budget Management (Account Heads, Income/Expense entries)
   - Fee Structure setup per class
   - Student Invoice Generation (based on the class's fee structure)
   - Fee Collection (record a payment against an invoice, auto-updates status)
===============================================================================
"""

import tkinter as tk
from tkinter import ttk
from datetime import date, timedelta

from db_config import get_connection
from utils import make_treeview, clear_tree, info, error


class FinanceModuleFrame(ttk.Frame):
    def __init__(self, parent, current_user):
        super().__init__(parent)
        self.current_user = current_user

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.heads_tab = ttk.Frame(notebook)
        self.budget_tab = ttk.Frame(notebook)
        self.fee_structure_tab = ttk.Frame(notebook)
        self.invoice_tab = ttk.Frame(notebook)
        self.collection_tab = ttk.Frame(notebook)

        notebook.add(self.heads_tab, text="Account Heads")
        notebook.add(self.budget_tab, text="Budget / Transactions")
        notebook.add(self.fee_structure_tab, text="Fee Structure")
        notebook.add(self.invoice_tab, text="Generate Invoice")
        notebook.add(self.collection_tab, text="Fee Collection")

        self._load_lookups()
        self._build_heads_tab()
        self._build_budget_tab()
        self._build_fee_structure_tab()
        self._build_invoice_tab()
        self._build_collection_tab()

    def _load_lookups(self):
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT class_id, class_name FROM classes ORDER BY class_order")
        self.class_map = {name: cid for cid, name in cur.fetchall()}
        cur.execute("SELECT academic_year_id FROM academic_years WHERE is_current=TRUE")
        row = cur.fetchone()
        self.current_year_id = row[0] if row else None
        cur.close(); conn.close()

    def _refresh_head_list(self):
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT head_id, head_name FROM account_heads ORDER BY head_name")
        rows = cur.fetchall(); cur.close(); conn.close()
        self.head_map = {name: hid for hid, name in rows}

    # ------------------------------------------------------------------ #
    # TAB 1: ACCOUNT HEADS
    # ------------------------------------------------------------------ #
    def _build_heads_tab(self):
        form = ttk.Frame(self.heads_tab)
        form.pack(fill="x", padx=15, pady=15)

        ttk.Label(form, text="Head Name:").grid(row=0, column=0, sticky="e", padx=5)
        self.head_name_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.head_name_var, width=25).grid(row=0, column=1, padx=5)

        ttk.Label(form, text="Type:").grid(row=0, column=2, sticky="e", padx=5)
        self.head_type_var = tk.StringVar(value="INCOME")
        ttk.Combobox(form, textvariable=self.head_type_var, values=["INCOME", "EXPENSE"],
                     state="readonly", width=12).grid(row=0, column=3, padx=5)

        ttk.Button(form, text="Add Head", command=self._add_head).grid(row=0, column=4, padx=10)

        cols = ("id", "name", "type")
        self.heads_tree, container = make_treeview(self.heads_tab, cols, height=12)
        container.pack(fill="both", expand=True, padx=15, pady=10)
        self._load_heads()

    def _add_head(self):
        name = self.head_name_var.get().strip()
        if not name:
            error("Missing Data", "Enter a head name.")
            return
        conn = get_connection(); cur = conn.cursor()
        try:
            cur.execute("INSERT INTO account_heads (head_name, head_type) VALUES (%s,%s)",
                        (name, self.head_type_var.get()))
            conn.commit()
            info("Added", f"Account head '{name}' added.")
            self.head_name_var.set("")
            self._load_heads()
        except Exception as e:
            conn.rollback()
            error("Database Error", str(e))
        finally:
            cur.close(); conn.close()

    def _load_heads(self):
        clear_tree(self.heads_tree)
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT head_id, head_name, head_type FROM account_heads ORDER BY head_type, head_name")
        for row in cur.fetchall():
            self.heads_tree.insert("", "end", values=row)
        cur.close(); conn.close()
        self._refresh_head_list()

    # ------------------------------------------------------------------ #
    # TAB 2: BUDGET / TRANSACTIONS (income & expense ledger + balance)
    # ------------------------------------------------------------------ #
    def _build_budget_tab(self):
        self._refresh_head_list()
        form = ttk.Frame(self.budget_tab)
        form.pack(fill="x", padx=15, pady=15)

        ttk.Label(form, text="Head:").grid(row=0, column=0, sticky="e", padx=5)
        self.txn_head_var = tk.StringVar()
        self.txn_head_combo = ttk.Combobox(form, textvariable=self.txn_head_var,
                                            values=list(self.head_map), state="readonly", width=20)
        self.txn_head_combo.grid(row=0, column=1, padx=5)

        ttk.Label(form, text="Date (YYYY-MM-DD):").grid(row=0, column=2, sticky="e", padx=5)
        self.txn_date_var = tk.StringVar(value=str(date.today()))
        ttk.Entry(form, textvariable=self.txn_date_var, width=15).grid(row=0, column=3, padx=5)

        ttk.Label(form, text="Amount:").grid(row=1, column=0, sticky="e", padx=5)
        self.txn_amount_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.txn_amount_var, width=15).grid(row=1, column=1, padx=5, sticky="w")

        ttk.Label(form, text="Description:").grid(row=1, column=2, sticky="e", padx=5)
        self.txn_desc_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.txn_desc_var, width=25).grid(row=1, column=3, padx=5)

        ttk.Button(form, text="Record Transaction", style="Accent.TButton",
                   command=self._record_transaction).grid(row=2, column=0, columnspan=2, pady=10)

        self.balance_label = ttk.Label(self.budget_tab, text="", style="SubHeader.TLabel")
        self.balance_label.pack(anchor="w", padx=15)

        cols = ("date", "head", "type", "amount", "description")
        self.txn_tree, container = make_treeview(self.budget_tab, cols, height=12)
        container.pack(fill="both", expand=True, padx=15, pady=10)
        self._load_transactions()

    def _record_transaction(self):
        head_id = self.head_map.get(self.txn_head_var.get())
        if not head_id or not self.current_year_id:
            error("Missing Data", "Select an account head.")
            return
        try:
            amount = float(self.txn_amount_var.get())
        except ValueError:
            error("Invalid Input", "Amount must be a number.")
            return
        conn = get_connection(); cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO budget_transactions (head_id, academic_year_id, txn_date, amount, description, recorded_by)
                VALUES (%s,%s,%s,%s,%s,%s)
            """, (head_id, self.current_year_id, self.txn_date_var.get(), amount,
                  self.txn_desc_var.get(), self.current_user.user_id))
            conn.commit()
            info("Recorded", "Transaction recorded.")
            self._load_transactions()
        except Exception as e:
            conn.rollback()
            error("Database Error", str(e))
        finally:
            cur.close(); conn.close()

    def _load_transactions(self):
        clear_tree(self.txn_tree)
        conn = get_connection(); cur = conn.cursor()
        cur.execute("""
            SELECT t.txn_date, h.head_name, h.head_type, t.amount, t.description
            FROM budget_transactions t JOIN account_heads h ON h.head_id = t.head_id
            ORDER BY t.txn_date DESC
        """)
        rows = cur.fetchall()
        for row in rows:
            self.txn_tree.insert("", "end", values=row)

        cur.execute("""
            SELECT
              SUM(CASE WHEN h.head_type='INCOME' THEN t.amount ELSE 0 END) AS income,
              SUM(CASE WHEN h.head_type='EXPENSE' THEN t.amount ELSE 0 END) AS expense
            FROM budget_transactions t JOIN account_heads h ON h.head_id = t.head_id
        """)
        income, expense = cur.fetchone()
        income = income or 0
        expense = expense or 0
        self.balance_label.config(text=f"Total Income: Rs.{income:.2f}   |   Total Expense: Rs.{expense:.2f}   "
                                        f"|   Net Balance: Rs.{income - expense:.2f}")
        cur.close(); conn.close()

    # ------------------------------------------------------------------ #
    # TAB 3: FEE STRUCTURE
    # ------------------------------------------------------------------ #
    def _build_fee_structure_tab(self):
        form = ttk.Frame(self.fee_structure_tab)
        form.pack(fill="x", padx=15, pady=15)

        ttk.Label(form, text="Class:").grid(row=0, column=0, sticky="e", padx=5)
        self.fs_class_var = tk.StringVar()
        ttk.Combobox(form, textvariable=self.fs_class_var, values=list(self.class_map),
                     state="readonly", width=15).grid(row=0, column=1, padx=5)

        ttk.Label(form, text="Head:").grid(row=0, column=2, sticky="e", padx=5)
        self.fs_head_var = tk.StringVar()
        self.fs_head_combo = ttk.Combobox(form, textvariable=self.fs_head_var,
                                           values=list(self.head_map), state="readonly", width=18)
        self.fs_head_combo.grid(row=0, column=3, padx=5)

        ttk.Label(form, text="Amount:").grid(row=1, column=0, sticky="e", padx=5)
        self.fs_amount_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.fs_amount_var, width=15).grid(row=1, column=1, padx=5, sticky="w")

        ttk.Label(form, text="Frequency:").grid(row=1, column=2, sticky="e", padx=5)
        self.fs_freq_var = tk.StringVar(value="MONTHLY")
        ttk.Combobox(form, textvariable=self.fs_freq_var,
                     values=["MONTHLY", "QUARTERLY", "ANNUALLY", "ONE_TIME"],
                     state="readonly", width=15).grid(row=1, column=3, padx=5)

        ttk.Button(form, text="Add to Fee Structure", style="Accent.TButton",
                   command=self._add_fee_structure).grid(row=2, column=0, columnspan=2, pady=10)

        cols = ("class", "head", "amount", "frequency")
        self.fs_tree, container = make_treeview(self.fee_structure_tab, cols, height=12)
        container.pack(fill="both", expand=True, padx=15, pady=10)
        self._load_fee_structure()

    def _add_fee_structure(self):
        class_id = self.class_map.get(self.fs_class_var.get())
        head_id = self.head_map.get(self.fs_head_var.get())
        if not (class_id and head_id and self.current_year_id):
            error("Missing Data", "Select class and head.")
            return
        try:
            amount = float(self.fs_amount_var.get())
        except ValueError:
            error("Invalid Input", "Amount must be a number.")
            return
        conn = get_connection(); cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO fee_structure (class_id, head_id, academic_year_id, amount, frequency)
                VALUES (%s,%s,%s,%s,%s)
            """, (class_id, head_id, self.current_year_id, amount, self.fs_freq_var.get()))
            conn.commit()
            info("Added", "Fee structure entry added.")
            self._load_fee_structure()
        except Exception as e:
            conn.rollback()
            error("Database Error", str(e))
        finally:
            cur.close(); conn.close()

    def _load_fee_structure(self):
        clear_tree(self.fs_tree)
        conn = get_connection(); cur = conn.cursor()
        cur.execute("""
            SELECT c.class_name, h.head_name, f.amount, f.frequency
            FROM fee_structure f
            JOIN classes c ON c.class_id = f.class_id
            JOIN account_heads h ON h.head_id = f.head_id
            ORDER BY c.class_order
        """)
        for row in cur.fetchall():
            self.fs_tree.insert("", "end", values=row)
        cur.close(); conn.close()

    # ------------------------------------------------------------------ #
    # TAB 4: GENERATE INVOICE (sums the student's class fee structure)
    # ------------------------------------------------------------------ #
    def _build_invoice_tab(self):
        form = ttk.Frame(self.invoice_tab)
        form.pack(fill="x", padx=15, pady=15)

        ttk.Label(form, text="Admission No:").grid(row=0, column=0, sticky="e", padx=5)
        self.inv_adm_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.inv_adm_var, width=20).grid(row=0, column=1, padx=5)

        ttk.Label(form, text="Due Date (YYYY-MM-DD):").grid(row=0, column=2, sticky="e", padx=5)
        self.inv_due_var = tk.StringVar(value=str(date.today() + timedelta(days=15)))
        ttk.Entry(form, textvariable=self.inv_due_var, width=15).grid(row=0, column=3, padx=5)

        ttk.Button(form, text="Generate Invoice", style="Accent.TButton",
                   command=self._generate_invoice).grid(row=1, column=0, columnspan=2, pady=10)

        self.invoice_result_box = tk.Text(self.invoice_tab, height=18, font=("Consolas", 10))
        self.invoice_result_box.pack(fill="both", expand=True, padx=15, pady=10)

    def _generate_invoice(self):
        adm_no = self.inv_adm_var.get().strip()
        due_date = self.inv_due_var.get().strip()
        conn = get_connection(); cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM students WHERE admission_no=%s", (adm_no,))
        student = cur.fetchone()
        if not student:
            error("Not Found", "No student with that admission number.")
            cur.close(); conn.close()
            return

        cur.execute("SELECT head_id, head_name, amount FROM fee_structure f "
                    "JOIN account_heads h ON h.head_id=f.head_id "
                    "WHERE f.class_id=%s AND f.academic_year_id=%s",
                    (student["class_id"], student["academic_year_id"]))
        items = cur.fetchall()
        if not items:
            error("Not Configured", "No fee structure defined for this student's class.")
            cur.close(); conn.close()
            return

        total = sum(i["amount"] for i in items)
        try:
            cur.execute("""
                INSERT INTO student_invoices (student_id, academic_year_id, invoice_date, due_date, total_amount, status)
                VALUES (%s,%s,%s,%s,%s,'UNPAID')
            """, (student["student_id"], student["academic_year_id"], date.today(), due_date, total))
            invoice_id = cur.lastrowid
            for i in items:
                cur.execute("INSERT INTO invoice_items (invoice_id, head_id, amount) VALUES (%s,%s,%s)",
                            (invoice_id, i["head_id"], i["amount"]))
            conn.commit()

            lines = [f"INVOICE #{invoice_id}", f"Student: {student['first_name']} {student['last_name'] or ''} "
                     f"({adm_no})", f"Due Date: {due_date}", "-" * 40]
            for i in items:
                lines.append(f"{i['head_name']:<25}{i['amount']:>10.2f}")
            lines.append("-" * 40)
            lines.append(f"{'TOTAL':<25}{total:>10.2f}")
            self.invoice_result_box.delete("1.0", "end")
            self.invoice_result_box.insert("1.0", "\n".join(lines))
            info("Invoice Generated", f"Invoice #{invoice_id} created for Rs.{total:.2f}")
        except Exception as e:
            conn.rollback()
            error("Database Error", str(e))
        finally:
            cur.close(); conn.close()

    # ------------------------------------------------------------------ #
    # TAB 5: FEE COLLECTION
    # ------------------------------------------------------------------ #
    def _build_collection_tab(self):
        top = ttk.Frame(self.collection_tab)
        top.pack(fill="x", padx=15, pady=15)
        ttk.Button(top, text="Refresh Unpaid/Partial Invoices", command=self._load_unpaid_invoices).pack(side="left")

        cols = ("invoice_id", "student", "total", "due_date", "status")
        self.inv_tree, container = make_treeview(self.collection_tab, cols, height=10)
        container.pack(fill="both", expand=True, padx=15, pady=10)

        pay_form = ttk.Frame(self.collection_tab)
        pay_form.pack(fill="x", padx=15, pady=10)
        ttk.Label(pay_form, text="Amount to Collect:").pack(side="left")
        self.pay_amount_var = tk.StringVar()
        ttk.Entry(pay_form, textvariable=self.pay_amount_var, width=15).pack(side="left", padx=5)
        ttk.Label(pay_form, text="Mode:").pack(side="left")
        self.pay_mode_var = tk.StringVar(value="CASH")
        ttk.Combobox(pay_form, textvariable=self.pay_mode_var, values=["CASH", "CARD", "ONLINE", "CHEQUE"],
                     state="readonly", width=12).pack(side="left", padx=5)
        ttk.Button(pay_form, text="Collect Payment", style="Accent.TButton",
                   command=self._collect_payment).pack(side="left", padx=10)

        self._load_unpaid_invoices()

    def _load_unpaid_invoices(self):
        clear_tree(self.inv_tree)
        conn = get_connection(); cur = conn.cursor()
        cur.execute("""
            SELECT i.invoice_id, CONCAT(s.first_name,' ',IFNULL(s.last_name,''),' (',s.admission_no,')'),
                   i.total_amount, i.due_date, i.status
            FROM student_invoices i JOIN students s ON s.student_id = i.student_id
            WHERE i.status IN ('UNPAID','PARTIALLY_PAID','OVERDUE')
            ORDER BY i.due_date
        """)
        for row in cur.fetchall():
            self.inv_tree.insert("", "end", values=row)
        cur.close(); conn.close()

    def _collect_payment(self):
        sel = self.inv_tree.selection()
        if not sel:
            error("No Selection", "Select an invoice first.")
            return
        invoice_id = self.inv_tree.item(sel[0])["values"][0]
        try:
            amount = float(self.pay_amount_var.get())
        except ValueError:
            error("Invalid Input", "Amount must be a number.")
            return

        conn = get_connection(); cur = conn.cursor(dictionary=True)
        cur.execute("SELECT total_amount FROM student_invoices WHERE invoice_id=%s", (invoice_id,))
        total = cur.fetchone()["total_amount"]
        cur.execute("SELECT IFNULL(SUM(amount_paid),0) AS paid FROM fee_payments WHERE invoice_id=%s", (invoice_id,))
        already_paid = cur.fetchone()["paid"]

        try:
            cur.execute("""
                INSERT INTO fee_payments (invoice_id, amount_paid, payment_date, payment_mode, received_by)
                VALUES (%s,%s,%s,%s,%s)
            """, (invoice_id, amount, date.today(), self.pay_mode_var.get(), self.current_user.user_id))

            new_total_paid = already_paid + amount
            new_status = "PAID" if new_total_paid >= total else "PARTIALLY_PAID"
            cur.execute("UPDATE student_invoices SET status=%s WHERE invoice_id=%s", (new_status, invoice_id))
            conn.commit()
            info("Payment Recorded", f"Rs.{amount:.2f} collected. Invoice status: {new_status}")
            self._load_unpaid_invoices()
        except Exception as e:
            conn.rollback()
            error("Database Error", str(e))
        finally:
            cur.close(); conn.close()