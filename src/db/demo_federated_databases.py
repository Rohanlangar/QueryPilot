"""Demo federated microservice databases setup for QueryPilot.

Creates and populates independent databases representing a microservices architecture:
  1. order_db.db     — orders, outbox_events
  2. inventory_db.db — inventory, processed_events
  3. payment_db.db   — payments
  4. analytics_db.db — order_metrics

Allows testing and demonstrating federated cross-database querying instantly.
"""

import os
import sqlite3
from typing import Dict
from db.connection_manager import register_database, DatabaseConfig

_DB_DIR = os.path.dirname(os.path.abspath(__file__))


def seed_order_db(db_path: str):
    """Seed order_db with orders and outbox events."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS outbox_events")
    cur.execute("DROP TABLE IF EXISTS orders")

    cur.execute("""
        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id VARCHAR(50) NOT NULL,
            customer_id VARCHAR(50) NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            status VARCHAR(30) NOT NULL,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE outbox_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            aggregate_type VARCHAR(50) NOT NULL,
            aggregate_id VARCHAR(50) NOT NULL,
            event_type VARCHAR(50) NOT NULL,
            payload TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    orders = [
        ("P001", "C001", 350, 120.0, "COMPLETED", "2026-09-01"),
        ("P001", "C002", 500, 120.0, "COMPLETED", "2026-09-02"),
        ("P002", "C003", 220, 85.0,  "COMPLETED", "2026-09-02"),
        ("P002", "C001", 200, 85.0,  "COMPLETED", "2026-09-03"),
        ("P003", "C004", 45,  350.0, "COMPLETED", "2026-09-04"),
        ("P004", "C005", 900, 25.0,  "COMPLETED", "2026-09-05"),
        ("P005", "C002", 15,  1500.0,"COMPLETED", "2026-09-06"),
    ]
    cur.executemany(
        "INSERT INTO orders (product_id, customer_id, quantity, unit_price, status, order_date) VALUES (?, ?, ?, ?, ?, ?)",
        orders,
    )

    outbox = [
        ("Order", "1", "OrderCreated", '{"order_id": 1, "product_id": "P001"}'),
        ("Order", "2", "OrderCreated", '{"order_id": 2, "product_id": "P001"}'),
    ]
    cur.executemany(
        "INSERT INTO outbox_events (aggregate_type, aggregate_id, event_type, payload) VALUES (?, ?, ?, ?)",
        outbox,
    )

    conn.commit()
    conn.close()


def seed_inventory_db(db_path: str):
    """Seed inventory_db with inventory and processed events."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS processed_events")
    cur.execute("DROP TABLE IF EXISTS inventory")

    cur.execute("""
        CREATE TABLE inventory (
            product_id VARCHAR(50) PRIMARY KEY,
            product_name VARCHAR(150) NOT NULL,
            category VARCHAR(50) NOT NULL,
            stock_quantity INTEGER NOT NULL,
            reorder_level INTEGER NOT NULL,
            warehouse_location VARCHAR(50) NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE processed_events (
            event_id VARCHAR(100) PRIMARY KEY,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    inventory_rows = [
        ("P001", "Ultra Wireless Headphones", "Electronics", 20, 50, "WH-East"),
        ("P002", "Smart Fitness Tracker", "Wearables", 15, 40, "WH-West"),
        ("P003", "Ergonomic Office Chair", "Furniture", 120, 20, "WH-Central"),
        ("P004", "USB-C Fast Charging Cable", "Accessories", 10, 100, "WH-East"),
        ("P005", "Professional 4K Drone", "Electronics", 80, 10, "WH-South"),
    ]
    cur.executemany(
        "INSERT INTO inventory (product_id, product_name, category, stock_quantity, reorder_level, warehouse_location) VALUES (?, ?, ?, ?, ?, ?)",
        inventory_rows,
    )

    conn.commit()
    conn.close()


def seed_payment_db(db_path: str):
    """Seed payment_db with payments."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS payments")

    cur.execute("""
        CREATE TABLE payments (
            payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            payment_method VARCHAR(50) NOT NULL,
            status VARCHAR(30) NOT NULL,
            payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    payments = [
        (1, 42000.0, "CreditCard", "SUCCESS", "2026-09-01"),
        (2, 60000.0, "BankTransfer", "SUCCESS", "2026-09-02"),
        (3, 18700.0, "CreditCard", "SUCCESS", "2026-09-02"),
        (4, 17000.0, "PayPal", "SUCCESS", "2026-09-03"),
        (5, 15750.0, "CreditCard", "SUCCESS", "2026-09-04"),
        (6, 22500.0, "CreditCard", "SUCCESS", "2026-09-05"),
        (7, 22500.0, "WireTransfer", "SUCCESS", "2026-09-06"),
    ]
    cur.executemany(
        "INSERT INTO payments (order_id, amount, payment_method, status, payment_date) VALUES (?, ?, ?, ?, ?)",
        payments,
    )

    conn.commit()
    conn.close()


def seed_analytics_db(db_path: str):
    """Seed analytics_db with order metrics."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS order_metrics")

    cur.execute("""
        CREATE TABLE order_metrics (
            metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
            month_year VARCHAR(20) NOT NULL,
            total_orders INTEGER NOT NULL,
            total_gross_revenue REAL NOT NULL,
            avg_fulfillment_hours REAL NOT NULL
        )
    """)

    metrics = [
        ("2026-07", 1450, 245000.0, 18.5),
        ("2026-08", 1820, 310000.0, 16.2),
        ("2026-09", 950, 198450.0, 14.8),
    ]
    cur.executemany(
        "INSERT INTO order_metrics (month_year, total_orders, total_gross_revenue, avg_fulfillment_hours) VALUES (?, ?, ?, ?)",
        metrics,
    )

    conn.commit()
    conn.close()


def initialize_demo_federated_databases() -> Dict[str, str]:
    """Initialize and register all demo microservice databases.

    Returns dict of {db_name: file_path}.
    """
    db_paths = {
        "order_db": os.path.join(_DB_DIR, "order_db.db"),
        "inventory_db": os.path.join(_DB_DIR, "inventory_db.db"),
        "payment_db": os.path.join(_DB_DIR, "payment_db.db"),
        "analytics_db": os.path.join(_DB_DIR, "analytics_db.db"),
    }

    seed_order_db(db_paths["order_db"])
    seed_inventory_db(db_paths["inventory_db"])
    seed_payment_db(db_paths["payment_db"])
    seed_analytics_db(db_paths["analytics_db"])

    for c_id, f_path in db_paths.items():
        register_database(
            DatabaseConfig(
                connection_id=c_id,
                db_type="sqlite",
                database=f_path,
            )
        )

    return db_paths


if __name__ == "__main__":
    paths = initialize_demo_federated_databases()
    print("Demo federated databases seeded and registered successfully:")
    for name, path in paths.items():
        print(f"  - {name}: {path}")
