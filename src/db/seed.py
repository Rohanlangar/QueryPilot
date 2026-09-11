"""Database seeder for demo SQLite database.

Creates a multi-table business database (company.db) with realistic data:
- departments
- employees
- salaries
- projects
- employee_projects
- customers
- orders
- order_items
"""

import os
import sqlite3
from datetime import date, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "company.db")


def seed_database(db_path: str = DB_PATH) -> str:
    """Initialize and populate SQLite database with test schema and records."""
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 1. Departments
    cur.execute("""
        CREATE TABLE departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            budget REAL NOT NULL,
            location TEXT NOT NULL
        )
    """)
    departments = [
        ("Engineering", 1500000.0, "Building A, Floor 3"),
        ("Sales", 800000.0, "Building B, Floor 1"),
        ("Marketing", 500000.0, "Building B, Floor 2"),
        ("Human Resources", 300000.0, "Building A, Floor 1"),
        ("Finance", 600000.0, "Building A, Floor 2"),
    ]
    cur.executemany("INSERT INTO departments (name, budget, location) VALUES (?, ?, ?)", departments)

    # 2. Employees (includes PII fields: email, phone)
    cur.execute("""
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            phone TEXT NOT NULL,
            hire_date TEXT NOT NULL,
            department_id INTEGER,
            job_title TEXT NOT NULL,
            FOREIGN KEY (department_id) REFERENCES departments (id)
        )
    """)
    employees = [
        ("Alice", "Johnson", "alice.johnson@company.com", "+1-555-0101", "2021-03-15", 1, "Principal Software Engineer"),
        ("Bob", "Smith", "bob.smith@company.com", "+1-555-0102", "2020-06-01", 1, "Staff Software Engineer"),
        ("Carol", "Williams", "carol.w@company.com", "+1-555-0103", "2022-01-10", 2, "Senior Account Executive"),
        ("David", "Brown", "david.brown@company.com", "+1-555-0104", "2019-11-20", 2, "Sales Director"),
        ("Eva", "Martinez", "eva.m@company.com", "+1-555-0105", "2023-04-05", 3, "Growth Marketing Lead"),
        ("Frank", "Miller", "frank.miller@company.com", "+1-555-0106", "2022-08-15", 4, "HR Specialist"),
        ("Grace", "Davis", "grace.davis@company.com", "+1-555-0107", "2020-02-01", 5, "Financial Controller"),
        ("Hank", "Wilson", "hank.wilson@company.com", "+1-555-0108", "2024-01-08", 1, "Junior DevOps Engineer"),
    ]
    cur.executemany(
        "INSERT INTO employees (first_name, last_name, email, phone, hire_date, department_id, job_title) VALUES (?, ?, ?, ?, ?, ?, ?)",
        employees
    )

    # 3. Salaries (Restricted table for RBAC checks)
    cur.execute("""
        CREATE TABLE salaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            effective_date TEXT NOT NULL,
            is_current INTEGER DEFAULT 1,
            FOREIGN KEY (employee_id) REFERENCES employees (id)
        )
    """)
    salaries = [
        (1, 165000.0, "2024-01-01", 1),
        (2, 140000.0, "2024-01-01", 1),
        (3, 95000.0, "2023-01-01", 1),
        (4, 180000.0, "2023-06-01", 1),
        (5, 110000.0, "2023-04-05", 1),
        (6, 75000.0, "2023-08-15", 1),
        (7, 135000.0, "2023-02-01", 1),
        (8, 85000.0, "2024-01-08", 1),
    ]
    cur.executemany(
        "INSERT INTO salaries (employee_id, amount, effective_date, is_current) VALUES (?, ?, ?, ?)",
        salaries
    )

    # 4. Projects
    cur.execute("""
        CREATE TABLE projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            budget REAL NOT NULL,
            status TEXT NOT NULL,
            department_id INTEGER,
            FOREIGN KEY (department_id) REFERENCES departments (id)
        )
    """)
    projects = [
        ("NextGen Cloud Migration", 450000.0, "In Progress", 1),
        ("AI Customer Copilot", 300000.0, "Planning", 1),
        ("Q4 Enterprise Sales Push", 150000.0, "Completed", 2),
        ("Brand Refresh 2026", 120000.0, "In Progress", 3),
    ]
    cur.executemany("INSERT INTO projects (name, budget, status, department_id) VALUES (?, ?, ?, ?)", projects)

    # 5. Employee Projects
    cur.execute("""
        CREATE TABLE employee_projects (
            employee_id INTEGER,
            project_id INTEGER,
            role TEXT NOT NULL,
            hours_allocated INTEGER NOT NULL,
            PRIMARY KEY (employee_id, project_id),
            FOREIGN KEY (employee_id) REFERENCES employees (id),
            FOREIGN KEY (project_id) REFERENCES projects (id)
        )
    """)
    emp_proj = [
        (1, 1, "Tech Lead", 30),
        (2, 1, "Core Engineer", 40),
        (1, 2, "Advisor", 10),
        (3, 3, "Account Executive", 35),
        (4, 3, "Executive Sponsor", 5),
        (5, 4, "Campaign Manager", 40),
        (8, 1, "Infrastructure Specialist", 40),
    ]
    cur.executemany("INSERT INTO employee_projects VALUES (?, ?, ?, ?)", emp_proj)

    # 6. Customers
    cur.execute("""
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            contact_email TEXT NOT NULL,
            contact_phone TEXT NOT NULL,
            country TEXT NOT NULL,
            tier TEXT NOT NULL
        )
    """)
    customers = [
        ("Acme Corp", "procurement@acme.com", "+1-555-8801", "USA", "Enterprise"),
        ("GlobalTech Solutions", "billing@globaltech.io", "+44-20-7946-0912", "UK", "Enterprise"),
        ("Nexus Ventures", "finance@nexusventures.de", "+49-30-123456", "Germany", "Mid-Market"),
        ("Starlight Media", "orders@starlightmedia.com", "+1-555-9922", "USA", "SMB"),
    ]
    cur.executemany(
        "INSERT INTO customers (company_name, contact_email, contact_phone, country, tier) VALUES (?, ?, ?, ?, ?)",
        customers
    )

    # 7. Orders
    cur.execute("""
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            order_date TEXT NOT NULL,
            total_amount REAL NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers (id)
        )
    """)
    orders = [
        (1, "2026-01-15", 45000.0, "Delivered"),
        (1, "2026-02-10", 30000.0, "Processing"),
        (2, "2026-01-20", 75000.0, "Delivered"),
        (3, "2026-03-01", 12500.0, "Pending"),
        (4, "2026-02-28", 8500.0, "Delivered"),
    ]
    cur.executemany("INSERT INTO orders (customer_id, order_date, total_amount, status) VALUES (?, ?, ?, ?)", orders)

    # 8. Order Items
    cur.execute("""
        CREATE TABLE order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders (id)
        )
    """)
    order_items = [
        (1, "Enterprise Platform License (Annual)", 1, 35000.0),
        (1, "Premium Support Add-on", 1, 10000.0),
        (2, "Dedicated Cluster Addon", 1, 30000.0),
        (3, "Custom API Integration", 1, 75000.0),
        (4, "Standard Analytics Seat Pack", 5, 2500.0),
        (5, "Base Platform Subscription", 1, 8500.0),
    ]
    cur.executemany("INSERT INTO order_items (order_id, product_name, quantity, unit_price) VALUES (?, ?, ?, ?)", order_items)

    conn.commit()
    conn.close()
    return db_path


if __name__ == "__main__":
    path = seed_database()
    print(f"Demo database seeded successfully at {path}")
