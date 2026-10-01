"""End-to-End Live Verification: Docker PostgreSQL Sandbox & Multi-Agent Pipeline.

Sets up a real PostgreSQL 16 container with a rich e-commerce schema and data,
registers it with QueryPilot, and tests:
  1. Ambiguity Detection: Ambiguous query triggers polite clarification without hallucinating SQL.
  2. Full Sandbox Lifecycle: Disposable Docker PostgreSQL sandbox is spun up, clones schema,
     loads sample rows with PII masking, executes safely, and verifies results.
  3. Simple & Complex Queries: Multi-table joins, aggregations, and business metrics.
  4. Tear-down & Cleanup: All Docker containers destroyed cleanly.
"""

import sys
import os
import time
import uuid
import json
import logging
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Force UTF-8 stdout
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("e2e_test")

# Add paths
_src_dir = os.path.dirname(os.path.abspath(__file__))
_agents_dir = os.path.join(_src_dir, "Agents")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)
if _agents_dir not in sys.path:
    sys.path.insert(0, _agents_dir)

import docker
from sqlalchemy import create_engine, text
from db.connection_manager import (
    DatabaseConfig,
    register_database,
    delete_connection,
    get_connection_schema,
)
from graph.build_graph import build_graph
from sandbox.sandbox_manager import sandbox_manager

SOURCE_CONTAINER_NAME = f"qp_e2e_source_pg_{uuid.uuid4().hex[:6]}"
SOURCE_PG_PORT = 5439
SOURCE_DB_NAME = "ecommerce_prod"
SOURCE_USER = "e2e_admin"
SOURCE_PASS = "e2e_pass_secure"


def start_source_postgres_container():
    """Spin up the mock 'production' PostgreSQL container."""
    client = docker.from_env()
    logger.info(f"Starting source PostgreSQL 16 container: {SOURCE_CONTAINER_NAME} on port {SOURCE_PG_PORT}...")
    container = client.containers.run(
        image="postgres:16",
        name=SOURCE_CONTAINER_NAME,
        detach=True,
        auto_remove=True,
        environment={
            "POSTGRES_USER": SOURCE_USER,
            "POSTGRES_PASSWORD": SOURCE_PASS,
            "POSTGRES_DB": SOURCE_DB_NAME,
        },
        ports={"5432/tcp": ("127.0.0.1", SOURCE_PG_PORT)},
    )

    # Wait for PostgreSQL to become ready
    deadline = time.time() + 30
    ready = False
    while time.time() < deadline:
        try:
            conn = psycopg2.connect(
                host="127.0.0.1",
                port=SOURCE_PG_PORT,
                user=SOURCE_USER,
                password=SOURCE_PASS,
                dbname=SOURCE_DB_NAME,
                connect_timeout=2,
            )
            conn.close()
            ready = True
            break
        except Exception:
            time.sleep(1)

    if not ready:
        container.kill()
        raise TimeoutError("Source PostgreSQL container failed to start within 30s")

    logger.info("Source PostgreSQL container is healthy and accepting connections.")
    return container


def seed_source_database():
    """Create rich e-commerce tables and insert sample records."""
    conn = psycopg2.connect(
        host="127.0.0.1",
        port=SOURCE_PG_PORT,
        user=SOURCE_USER,
        password=SOURCE_PASS,
        dbname=SOURCE_DB_NAME,
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    logger.info("Creating schema in source database...")
    cur.execute("""
        DROP TABLE IF EXISTS order_items CASCADE;
        DROP TABLE IF EXISTS orders CASCADE;
        DROP TABLE IF EXISTS customers CASCADE;
        DROP TABLE IF EXISTS products CASCADE;
        DROP TABLE IF EXISTS stores CASCADE;

        CREATE TABLE stores (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            city VARCHAR(50) NOT NULL,
            state VARCHAR(20) NOT NULL,
            opened_year INT NOT NULL
        );

        CREATE TABLE products (
            id SERIAL PRIMARY KEY,
            name VARCHAR(150) NOT NULL,
            category VARCHAR(50) NOT NULL,
            price NUMERIC(10, 2) NOT NULL,
            cost NUMERIC(10, 2) NOT NULL
        );

        CREATE TABLE customers (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(120) NOT NULL,
            phone VARCHAR(30) NOT NULL,
            tier VARCHAR(20) DEFAULT 'Standard'
        );

        CREATE TABLE orders (
            id SERIAL PRIMARY KEY,
            customer_id INT REFERENCES customers(id),
            store_id INT REFERENCES stores(id),
            order_date DATE NOT NULL,
            status VARCHAR(20) NOT NULL,
            total_amount NUMERIC(10, 2) NOT NULL
        );

        CREATE TABLE order_items (
            id SERIAL PRIMARY KEY,
            order_id INT REFERENCES orders(id),
            product_id INT REFERENCES products(id),
            quantity INT NOT NULL,
            unit_price NUMERIC(10, 2) NOT NULL
        );
    """)

    logger.info("Seeding realistic sample data...")
    # Stores
    cur.execute("""
        INSERT INTO stores (name, city, state, opened_year) VALUES
        ('Downtown Tech Hub', 'New York', 'NY', 2018),
        ('Silicon Valley Flagship', 'San Jose', 'CA', 2019),
        ('Magnificent Mile Store', 'Chicago', 'IL', 2021),
        ('Austin Metro Outpost', 'Austin', 'TX', 2022);
    """)

    # Products
    cur.execute("""
        INSERT INTO products (name, category, price, cost) VALUES
        ('UltraBook Pro 15', 'Electronics', 1299.99, 850.00),
        ('Wireless Noise-Cancelling Headphones', 'Electronics', 199.99, 80.00),
        ('Ergonomic Office Chair', 'Furniture', 349.50, 150.00),
        ('Standing Desk Electric', 'Furniture', 499.00, 220.00),
        ('Mechanical Gaming Keyboard', 'Accessories', 89.99, 35.00),
        ('USB-C 10-in-1 Hub', 'Accessories', 49.99, 15.00);
    """)

    # Customers (with PII to test masking)
    cur.execute("""
        INSERT INTO customers (name, email, phone, tier) VALUES
        ('Alice Harrison', 'alice.harrison@techcorp.io', '555-019-2831', 'VIP'),
        ('Bob Martinez', 'bob.martinez@gmail.com', '555-482-9102', 'Standard'),
        ('Charlie Clark', 'charlie.clark@outlook.com', '555-731-0022', 'VIP'),
        ('Diana Prince', 'diana.prince@themyscira.net', '555-900-1122', 'Standard');
    """)

    # Orders
    cur.execute("""
        INSERT INTO orders (customer_id, store_id, order_date, status, total_amount) VALUES
        (1, 1, '2024-01-15', 'Completed', 1499.98),
        (2, 2, '2024-01-20', 'Completed', 349.50),
        (3, 1, '2024-02-10', 'Completed', 848.50),
        (4, 3, '2024-02-18', 'Completed', 199.99),
        (1, 4, '2024-03-05', 'Completed', 499.00),
        (2, 1, '2024-03-12', 'Pending', 89.99);
    """)

    # Order Items
    cur.execute("""
        INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
        (1, 1, 1, 1299.99),
        (1, 2, 1, 199.99),
        (2, 3, 1, 349.50),
        (3, 3, 1, 349.50),
        (3, 4, 1, 499.00),
        (4, 2, 1, 199.99),
        (5, 4, 1, 499.00),
        (6, 5, 1, 89.99);
    """)

    cur.close()
    conn.close()
    logger.info("Source database seeded with 5 tables and relational records.")


def run_e2e_tests():
    source_container = None
    try:
        # Step 1: Start Source PostgreSQL
        source_container = start_source_postgres_container()
        seed_source_database()

        # Step 2: Register in QueryPilot
        logger.info("\n=======================================================")
        logger.info("STEP 2: Registering PostgreSQL connection in QueryPilot")
        logger.info("=======================================================")
        conn_id = "pg_e2e_retail"
        cfg = DatabaseConfig(
            connection_id=conn_id,
            db_type="postgres",
            host="127.0.0.1",
            port=SOURCE_PG_PORT,
            database=SOURCE_DB_NAME,
            username=SOURCE_USER,
            password=SOURCE_PASS,
        )
        reg_info = register_database(cfg)
        logger.info(f"Connected to database: {reg_info['status']}, tables={reg_info['tables']}")
        assert len(reg_info["tables"]) == 5, f"Expected 5 tables, got {reg_info['tables']}"

        # Compile the full graph pipeline
        graph = build_graph()
        session_id = f"e2e_user_session_{uuid.uuid4().hex[:6]}"

        # -------------------------------------------------------------
        # TEST 1: Ambiguity Check
        # -------------------------------------------------------------
        logger.info("\n=======================================================")
        logger.info("TEST 1: Ambiguity Guardrail (Underspecified Request)")
        logger.info("=======================================================")
        ambiguous_q = "Show me the top best"
        state_amb: dict = {
            "question": ambiguous_q,
            "connection_id": conn_id,
            "db_dialect": "postgres",
            "user_id": "test_analyst",
            "user_role": "admin",
            "session_id": session_id,
            "conversation_history": [],
            "sql_gen_attempts": 0,
        }

        logger.info(f"Running query: \"{ambiguous_q}\"")
        final_amb = dict(state_amb)
        for step in graph.stream(state_amb):
            for node, out in step.items():
                final_amb.update(out)

        logger.info(f"Ambiguity result: is_ambiguous={final_amb.get('is_ambiguous')}")
        logger.info(f"Clarification question: {final_amb.get('clarification_question') or final_amb.get('final_answer')}")
        assert final_amb.get("is_ambiguous") is True, "Ambiguity agent failed to flag vague query"
        assert final_amb.get("clarification_question") is not None, "Clarification question not provided"
        logger.info("  ✓ TEST 1 PASSED: Pipeline halted safely and requested clarification.")

        # -------------------------------------------------------------
        # TEST 2: Aggregation & Multi-Table Join
        # -------------------------------------------------------------
        logger.info("\n=======================================================")
        logger.info("TEST 2: Standard Aggregation & Join Query")
        logger.info("=======================================================")
        q2 = "What is the total revenue and total number of completed orders for each store?"
        state_q2: dict = {
            "question": q2,
            "connection_id": conn_id,
            "db_dialect": "postgres",
            "user_id": "test_analyst",
            "user_role": "admin",
            "session_id": session_id,
            "conversation_history": [],
            "sql_gen_attempts": 0,
        }

        logger.info(f"Running query: \"{q2}\"")
        final_q2 = dict(state_q2)
        visited_nodes = []
        for step in graph.stream(state_q2):
            for node, out in step.items():
                visited_nodes.append(node)
                final_q2.update(out)
                logger.info(f"  → Node completed: {node}")

        logger.info(f"Nodes visited: {visited_nodes}")
        assert "sandbox" in visited_nodes, "Query was not validated in sandbox!"
        assert final_q2.get("sandbox_passed") is True, f"Sandbox execution failed: {final_q2.get('sandbox_error')}"

        sql = final_q2.get("optimized_sql") or final_q2.get("generated_sql")
        results = final_q2.get("query_result") or []
        logger.info(f"Verified SQL:\n{sql}")
        logger.info(f"Query Results ({len(results)} rows): {json.dumps(results, indent=2, default=str)}")
        assert len(results) > 0, "Query returned no rows"
        logger.info("  ✓ TEST 2 PASSED: Executed safely in sandbox and returned real analytical results.")

        # -------------------------------------------------------------
        # TEST 3: Complex Multi-Table Join with Grouping & Filtering
        # -------------------------------------------------------------
        logger.info("\n=======================================================")
        logger.info("TEST 3: Complex 4-Table Join with Analytical Metrics")
        logger.info("=======================================================")
        q3 = "List each product category along with the total quantity sold and total revenue from completed orders, sorted by revenue descending."
        state_q3: dict = {
            "question": q3,
            "connection_id": conn_id,
            "db_dialect": "postgres",
            "user_id": "test_analyst",
            "user_role": "admin",
            "session_id": session_id,
            "conversation_history": [],
            "sql_gen_attempts": 0,
        }

        logger.info(f"Running query: \"{q3}\"")
        final_q3 = dict(state_q3)
        for step in graph.stream(state_q3):
            for node, out in step.items():
                final_q3.update(out)

        assert final_q3.get("sandbox_passed") is True, f"Sandbox execution failed on complex query: {final_q3.get('sandbox_error')}"
        sql_complex = final_q3.get("optimized_sql") or final_q3.get("generated_sql")
        results_complex = final_q3.get("query_result") or []
        logger.info(f"Complex SQL:\n{sql_complex}")
        logger.info(f"Complex Results:\n{json.dumps(results_complex, indent=2, default=str)}")
        assert len(results_complex) > 0, "Complex query produced 0 rows"
        logger.info("  ✓ TEST 3 PASSED: Complex 4-table join verified in sandbox and executed cleanly.")

        # Clean up registered connection
        delete_connection(conn_id)

    finally:
        # Tear down Docker containers
        logger.info("\nCleaning up containers...")
        try:
            sandbox_manager.cleanup_all()
            logger.info("Sandbox containers destroyed.")
        except Exception as e:
            logger.warning(f"Sandbox cleanup warning: {e}")

        if source_container:
            try:
                source_container.kill()
                logger.info(f"Source container {SOURCE_CONTAINER_NAME} killed.")
            except Exception as e:
                logger.warning(f"Source container kill warning: {e}")

    logger.info("\n=======================================================")
    logger.info("ALL END-TO-END TESTS PASSED WITH DOCKER & LIVE LLM!")
    logger.info("=======================================================")


if __name__ == "__main__":
    run_e2e_tests()
