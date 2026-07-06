"""
===============================================================================
 auth.py
-------------------------------------------------------------------------------
 Handles:
   - Verifying username/password against the `users` table (hash + salt)
   - Loading the logged-in user's role and permission set (ACL)
   - A reusable Tkinter LoginFrame that main.py shows before the dashboard
   - A simple `require_permission` guard other modules can call before
     letting a user perform a sensitive action (e.g. FEE_COLLECT)
===============================================================================
"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime

from db_config import get_connection, hash_password
from utils import COLORS, info, error


# ---------------------------------------------------------------------------
# CORE AUTH LOGIC (no GUI dependency - reusable, testable)
# ---------------------------------------------------------------------------
class CurrentUser:
    """Simple in-memory session object created after a successful login."""
    def __init__(self, row, permissions):
        self.user_id = row["user_id"]
        self.username = row["username"]
        self.full_name = row["full_name"]
        self.role_id = row["role_id"]
        self.role_name = row["role_name"]
        self.linked_student_id = row["linked_student_id"]
        self.linked_employee_id = row["linked_employee_id"]
        self.permissions = permissions  # set of permission_key strings

    def has_permission(self, permission_key: str) -> bool:
        return permission_key in self.permissions

    def __repr__(self):
        return f"<CurrentUser {self.username} ({self.role_name})>"


def authenticate(username: str, password: str):
    """
    Verifies credentials against the DB.
    Returns a CurrentUser instance on success, or None on failure.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT u.user_id, u.username, u.password_hash, u.salt, u.full_name,
                   u.role_id, r.role_name, u.linked_student_id, u.linked_employee_id,
                   u.is_active
            FROM users u
            JOIN roles r ON r.role_id = u.role_id
            WHERE u.username = %s
        """, (username,))
        row = cursor.fetchone()

        if not row or not row["is_active"]:
            return None

        computed_hash, _ = hash_password(password, row["salt"])
        if computed_hash != row["password_hash"]:
            return None

        # Fetch this role's permission set (the ACL grid)
        cursor.execute("""
            SELECT p.permission_key
            FROM role_permissions rp
            JOIN permissions p ON p.permission_id = rp.permission_id
            WHERE rp.role_id = %s
        """, (row["role_id"],))
        permissions = {r["permission_key"] for r in cursor.fetchall()}

        # Update last_login timestamp
        cursor.execute("UPDATE users SET last_login = %s WHERE user_id = %s",
                       (datetime.now(), row["user_id"]))
        conn.commit()

        return CurrentUser(row, permissions)
    finally:
        cursor.close()
        conn.close()


def require_permission(user: CurrentUser, permission_key: str) -> bool:
    """Guard helper: modules call this before a sensitive DB write.
    Shows an error popup and returns False if the user lacks the permission."""
    if user is None or not user.has_permission(permission_key):
        error("Access Denied", f"Your role ('{user.role_name if user else 'Guest'}') "
                                f"does not have the '{permission_key}' permission.")
        return False
    return True


# ---------------------------------------------------------------------------
# LOGIN SCREEN (Tkinter)
# ---------------------------------------------------------------------------
class LoginFrame(ttk.Frame):
    """
    Shown first when the app launches. On successful login it calls
    `on_success(current_user)` which main.py uses to build the dashboard.
    """
    def __init__(self, parent, on_success):
        super().__init__(parent, style="TFrame")
        self.on_success = on_success
        self._build_ui()

    def _build_ui(self):
        card = tk.Frame(self, bg="white", bd=1, relief="solid")
        card.place(relx=0.5, rely=0.5, anchor="center", width=380, height=340)

        tk.Label(card, text="School Management System", bg="white",
                 fg=COLORS["primary"], font=("Segoe UI", 15, "bold")).pack(pady=(25, 5))
        tk.Label(card, text="Please sign in to continue", bg="white",
                 fg="#555555", font=("Segoe UI", 9)).pack(pady=(0, 20))

        form = tk.Frame(card, bg="white")
        form.pack(pady=5)

        tk.Label(form, text="Username", bg="white", anchor="w").grid(row=0, column=0, sticky="w", pady=(5, 0))
        self.username_entry = ttk.Entry(form, width=30)
        self.username_entry.grid(row=1, column=0, pady=(0, 10))

        tk.Label(form, text="Password", bg="white", anchor="w").grid(row=2, column=0, sticky="w")
        self.password_entry = ttk.Entry(form, width=30, show="*")
        self.password_entry.grid(row=3, column=0, pady=(0, 15))
        self.password_entry.bind("<Return>", lambda e: self._attempt_login())

        login_btn = tk.Button(card, text="Login", bg=COLORS["primary"], fg="white",
                               font=("Segoe UI", 10, "bold"), relief="flat", width=20,
                               command=self._attempt_login)
        login_btn.pack(pady=5)

        tk.Label(card, text="Demo: admin / Admin@123", bg="white",
                 fg="#999999", font=("Segoe UI", 8)).pack(pady=(15, 0))

        self.username_entry.focus_set()

    def _attempt_login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()

        if not username or not password:
            error("Login Failed", "Please enter both username and password.")
            return

        try:
            user = authenticate(username, password)
        except Exception as e:
            error("Database Error", f"Could not reach the database:\n{e}")
            return

        if user is None:
            error("Login Failed", "Invalid username/password, or account is inactive.")
            return

        info("Welcome", f"Logged in as {user.full_name} ({user.role_name})")
        self.on_success(user)