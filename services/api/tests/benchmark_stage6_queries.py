import os
import sys
import time
import uuid
import json
import math
import sqlite3
from datetime import datetime, timezone, timedelta

def percentile(data, p):
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_data[int(k)]
    d0 = sorted_data[int(f)] * (c - k)
    d1 = sorted_data[int(c)] * (k - f)
    return d0 + d1


def run_performance_benchmark():
    print("================================================================================")
    print("OZHZO VERSE — STAGE 6 HIGH-VOLUME DATABASE PERFORMANCE BENCHMARK")
    print("Target Scale: 10,000 Users, 5,000 Homes, 100k Tasks, 100k Notifications, 100k Memories...")
    print("================================================================================")

    db_path = "/tmp/ozhzo_benchmark_stage6.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA cache_size = 100000;")
    cursor = conn.cursor()

    # 1. Create Schema
    cursor.executescript("""
    CREATE TABLE users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1,
        system_role TEXT NOT NULL DEFAULT 'USER',
        deleted_at TEXT
    );

    CREATE TABLE homes (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        public_home_id TEXT UNIQUE,
        currency TEXT NOT NULL DEFAULT 'USD',
        timezone TEXT NOT NULL DEFAULT 'UTC',
        status TEXT NOT NULL DEFAULT 'ACTIVE',
        deleted_at TEXT
    );

    CREATE TABLE home_members (
        id TEXT PRIMARY KEY,
        home_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'MEMBER',
        joined_at TEXT NOT NULL
    );

    CREATE TABLE tasks (
        id TEXT PRIMARY KEY,
        home_id TEXT NOT NULL,
        title TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'TODO',
        priority TEXT NOT NULL DEFAULT 'MEDIUM',
        due_date TEXT,
        created_at TEXT NOT NULL
    );

    CREATE TABLE inventory_items (
        id TEXT PRIMARY KEY,
        home_id TEXT NOT NULL,
        name TEXT NOT NULL,
        quantity REAL NOT NULL DEFAULT 1.0,
        unit TEXT NOT NULL DEFAULT 'units',
        min_threshold REAL NOT NULL DEFAULT 2.0,
        is_low_stock INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL
    );

    CREATE TABLE notifications (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        home_id TEXT,
        title TEXT NOT NULL,
        priority TEXT NOT NULL DEFAULT 'NORMAL',
        is_read INTEGER NOT NULL DEFAULT 0,
        is_resolved INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        dedup_key TEXT
    );

    CREATE TABLE audit_logs (
        id TEXT PRIMARY KEY,
        home_id TEXT,
        user_id TEXT,
        action TEXT NOT NULL,
        resource_type TEXT NOT NULL,
        created_at TEXT NOT NULL
    );

    CREATE TABLE automation_rules (
        id TEXT PRIMARY KEY,
        home_id TEXT NOT NULL,
        name TEXT NOT NULL,
        trigger_type TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'ACTIVE',
        created_at TEXT NOT NULL
    );

    CREATE TABLE automation_executions (
        id TEXT PRIMARY KEY,
        automation_id TEXT NOT NULL,
        home_id TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'SUCCESS',
        duration_ms INTEGER NOT NULL DEFAULT 10,
        idempotency_key TEXT,
        created_at TEXT NOT NULL
    );

    CREATE TABLE household_memories (
        id TEXT PRIMARY KEY,
        home_id TEXT NOT NULL,
        category TEXT NOT NULL DEFAULT 'PREFERENCE',
        content TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'ACTIVE',
        created_at TEXT NOT NULL
    );

    -- Composite Performance Indexes
    CREATE INDEX idx_users_email ON users(email);
    CREATE INDEX idx_members_user_home ON home_members(user_id, home_id);
    CREATE INDEX idx_members_home_role ON home_members(home_id, role);
    CREATE INDEX idx_tasks_home_status_due ON tasks(home_id, status, due_date);
    CREATE INDEX idx_inv_home_low ON inventory_items(home_id, is_low_stock);
    CREATE INDEX idx_notif_user_prio_read ON notifications(user_id, priority, is_read, created_at);
    CREATE INDEX idx_audit_home_time ON audit_logs(home_id, created_at DESC);
    CREATE INDEX idx_auto_home_status ON automation_rules(home_id, status);
    CREATE INDEX idx_auto_exec_home_time ON automation_executions(home_id, created_at DESC);
    CREATE INDEX idx_hh_mem_home_status ON household_memories(home_id, status);
    CREATE INDEX idx_hh_mem_home_cat ON household_memories(home_id, category);
    """)
    conn.commit()

    # 2. Bulk Seed Data
    print("Generating and seeding datasets...")
    t0 = time.time()

    NUM_USERS = 10000
    NUM_HOMES = 5000
    NUM_ITEMS_PER_100K = 100000

    # A. Users
    user_ids = [str(uuid.uuid4()) for _ in range(NUM_USERS)]
    users_data = [(u_id, f"user_{i}@ozhzo.com", "argon2_hash_mock_value", 1, "USER", None) for i, u_id in enumerate(user_ids)]
    cursor.executemany("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?);", users_data)

    # B. Homes & Members
    home_ids = [str(uuid.uuid4()) for _ in range(NUM_HOMES)]
    homes_data = [(h_id, f"Home Suite {i}", f"OZH-CODE-{i:06d}", "USD", "UTC", "ACTIVE", None) for i, h_id in enumerate(home_ids)]
    cursor.executemany("INSERT INTO homes VALUES (?, ?, ?, ?, ?, ?, ?);", homes_data)

    members_data = []
    for i, h_id in enumerate(home_ids):
        u_id = user_ids[i % NUM_USERS]
        members_data.append((str(uuid.uuid4()), h_id, u_id, "OWNER", datetime.now(timezone.utc).isoformat()))
        u_id2 = user_ids[(i + 1) % NUM_USERS]
        members_data.append((str(uuid.uuid4()), h_id, u_id2, "MEMBER", datetime.now(timezone.utc).isoformat()))
    cursor.executemany("INSERT INTO home_members VALUES (?, ?, ?, ?, ?);", members_data)

    # C. Tasks (100k)
    now_iso = datetime.now(timezone.utc).isoformat()
    tasks_data = []
    for i in range(NUM_ITEMS_PER_100K):
        h_id = home_ids[i % NUM_HOMES]
        tasks_data.append((
            str(uuid.uuid4()),
            h_id,
            f"Household Maintenance Task {i}",
            "TODO" if i % 2 == 0 else "COMPLETED",
            "HIGH" if i % 3 == 0 else "MEDIUM",
            now_iso,
            now_iso
        ))
    cursor.executemany("INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?);", tasks_data)

    # D. Inventory (50k)
    inv_data = []
    for i in range(50000):
        h_id = home_ids[i % NUM_HOMES]
        inv_data.append((
            str(uuid.uuid4()),
            h_id,
            f"Pantry Item {i % 500}",
            float(i % 10),
            "kg",
            2.0,
            1 if (i % 10) < 2 else 0,
            now_iso
        ))
    cursor.executemany("INSERT INTO inventory_items VALUES (?, ?, ?, ?, ?, ?, ?, ?);", inv_data)

    # E. Notifications (100k)
    notif_data = []
    for i in range(NUM_ITEMS_PER_100K):
        u_id = user_ids[i % NUM_USERS]
        h_id = home_ids[i % NUM_HOMES]
        notif_data.append((
            str(uuid.uuid4()),
            u_id,
            h_id,
            f"Alert: Household Notice {i}",
            "URGENT" if i % 10 == 0 else "NORMAL",
            0 if i % 4 == 0 else 1,
            0,
            now_iso,
            f"dedup-{i}"
        ))
    cursor.executemany("INSERT INTO notifications VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);", notif_data)

    # F. Audit Logs (100k)
    audit_data = []
    for i in range(NUM_ITEMS_PER_100K):
        h_id = home_ids[i % NUM_HOMES]
        u_id = user_ids[i % NUM_USERS]
        audit_data.append((
            str(uuid.uuid4()),
            h_id,
            u_id,
            "TASK_COMPLETED" if i % 2 == 0 else "INVENTORY_CONSUMED",
            "task",
            now_iso
        ))
    cursor.executemany("INSERT INTO audit_logs VALUES (?, ?, ?, ?, ?, ?);", audit_data)

    # G. Automations & Executions (100k)
    auto_data = []
    for i in range(10000):
        h_id = home_ids[i % NUM_HOMES]
        auto_data.append((
            str(uuid.uuid4()),
            h_id,
            f"Auto Restock Rule {i}",
            "INVENTORY_LOW",
            "ACTIVE",
            now_iso
        ))
    cursor.executemany("INSERT INTO automation_rules VALUES (?, ?, ?, ?, ?, ?);", auto_data)

    exec_data = []
    for i in range(NUM_ITEMS_PER_100K):
        h_id = home_ids[i % NUM_HOMES]
        exec_data.append((
            str(uuid.uuid4()),
            str(uuid.uuid4()),
            h_id,
            "SUCCESS" if i % 20 != 0 else "FAILED",
            8 + (i % 15),
            f"idemp-{i}",
            now_iso
        ))
    cursor.executemany("INSERT INTO automation_executions VALUES (?, ?, ?, ?, ?, ?, ?);", exec_data)

    # H. Household Memories (100k)
    mem_data = []
    categories = ["PREFERENCE", "ROUTINE", "IMPORTANT_FACT", "HOUSEHOLD_PATTERN", "RECURRING_BEHAVIOR"]
    for i in range(NUM_ITEMS_PER_100K):
        h_id = home_ids[i % NUM_HOMES]
        mem_data.append((
            str(uuid.uuid4()),
            h_id,
            categories[i % len(categories)],
            f"Resident preference fact {i}: Prefers organic groceries and weekday quiet hours at 10 PM.",
            "ACTIVE",
            now_iso
        ))
    cursor.executemany("INSERT INTO household_memories VALUES (?, ?, ?, ?, ?, ?);", mem_data)

    conn.commit()
    seed_duration = time.time() - t0
    print(f"Data seeding complete in {seed_duration:.2f}s.")
    print("================================================================================")
    print("RUNNING QUERY LATENCY MEASUREMENTS (200 Iterations per Operation)")
    print("================================================================================")

    benchmark_results = {}
    NUM_ITERS = 200

    # 1. Login Query (User lookup by email)
    latencies = []
    for k in range(NUM_ITERS):
        email = f"user_{k * 43 % NUM_USERS}@ozhzo.com"
        t_start = time.perf_counter()
        cursor.execute("SELECT id, password_hash, is_active, system_role FROM users WHERE email = ? AND deleted_at IS NULL;", (email,))
        cursor.fetchone()
        latencies.append((time.perf_counter() - t_start) * 1000)
    benchmark_results["User Login Lookup"] = latencies

    # 2. Home Dashboard Aggregation
    latencies = []
    for k in range(NUM_ITERS):
        h_id = home_ids[k * 17 % NUM_HOMES]
        t_start = time.perf_counter()
        cursor.execute("SELECT id, name, currency FROM homes WHERE id = ? AND deleted_at IS NULL;", (h_id,))
        cursor.fetchone()
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE home_id = ? AND status = 'TODO';", (h_id,))
        cursor.fetchone()
        cursor.execute("SELECT COUNT(*) FROM inventory_items WHERE home_id = ? AND is_low_stock = 1;", (h_id,))
        cursor.fetchone()
        latencies.append((time.perf_counter() - t_start) * 1000)
    benchmark_results["Home Dashboard Aggregation"] = latencies

    # 3. Global Search (Indexed search across Tasks, Inventory, and Memories)
    latencies = []
    for k in range(NUM_ITERS):
        h_id = home_ids[k * 19 % NUM_HOMES]
        term = f"%Task {k % 50}%"
        t_start = time.perf_counter()
        cursor.execute("SELECT id, title FROM tasks WHERE home_id = ? AND title LIKE ? LIMIT 10;", (h_id, term))
        cursor.fetchall()
        cursor.execute("SELECT id, name FROM inventory_items WHERE home_id = ? AND name LIKE ? LIMIT 10;", (h_id, term))
        cursor.fetchall()
        latencies.append((time.perf_counter() - t_start) * 1000)
    benchmark_results["Global Search Multi-Domain"] = latencies

    # 4. Notification Retrieval (Filtered by user, priority, unread)
    latencies = []
    for k in range(NUM_ITERS):
        u_id = user_ids[k * 31 % NUM_USERS]
        t_start = time.perf_counter()
        cursor.execute("""
            SELECT id, title, priority, is_read, created_at
            FROM notifications
            WHERE user_id = ? AND is_resolved = 0
            ORDER BY priority DESC, created_at DESC
            LIMIT 20;
        """, (u_id,))
        cursor.fetchall()
        latencies.append((time.perf_counter() - t_start) * 1000)
    benchmark_results["Notification Retrieval"] = latencies

    # 5. Task Listing (Scoped by Home, Status, and Due Date)
    latencies = []
    for k in range(NUM_ITERS):
        h_id = home_ids[k * 23 % NUM_HOMES]
        t_start = time.perf_counter()
        cursor.execute("""
            SELECT id, title, priority, due_date
            FROM tasks
            WHERE home_id = ? AND status = 'TODO'
            ORDER BY due_date ASC
            LIMIT 30;
        """, (h_id,))
        cursor.fetchall()
        latencies.append((time.perf_counter() - t_start) * 1000)
    benchmark_results["Task Listing & Filtering"] = latencies

    # 6. Inventory Listing (Scoped by Home & Stock Status)
    latencies = []
    for k in range(NUM_ITERS):
        h_id = home_ids[k * 11 % NUM_HOMES]
        t_start = time.perf_counter()
        cursor.execute("""
            SELECT id, name, quantity, unit, is_low_stock
            FROM inventory_items
            WHERE home_id = ?
            ORDER BY is_low_stock DESC, name ASC
            LIMIT 50;
        """, (h_id,))
        cursor.fetchall()
        latencies.append((time.perf_counter() - t_start) * 1000)
    benchmark_results["Inventory Listing"] = latencies

    # 7. Automation Listing (Rules per Home)
    latencies = []
    for k in range(NUM_ITERS):
        h_id = home_ids[k * 7 % NUM_HOMES]
        t_start = time.perf_counter()
        cursor.execute("""
            SELECT id, name, trigger_type, status
            FROM automation_rules
            WHERE home_id = ? AND status = 'ACTIVE'
            ORDER BY created_at DESC;
        """, (h_id,))
        cursor.fetchall()
        latencies.append((time.perf_counter() - t_start) * 1000)
    benchmark_results["Automation Rules Listing"] = latencies

    # 8. Automation Execution History (Paginated 90-day history)
    latencies = []
    for k in range(NUM_ITERS):
        h_id = home_ids[k * 13 % NUM_HOMES]
        t_start = time.perf_counter()
        cursor.execute("""
            SELECT id, automation_id, status, duration_ms, created_at
            FROM automation_executions
            WHERE home_id = ?
            ORDER BY created_at DESC
            LIMIT 25;
        """, (h_id,))
        cursor.fetchall()
        latencies.append((time.perf_counter() - t_start) * 1000)
    benchmark_results["Automation Execution History"] = latencies

    # 9. Household Memory Context Retrieval
    latencies = []
    for k in range(NUM_ITERS):
        h_id = home_ids[k * 29 % NUM_HOMES]
        cat = categories[k % len(categories)]
        t_start = time.perf_counter()
        cursor.execute("""
            SELECT id, category, content
            FROM household_memories
            WHERE home_id = ? AND status = 'ACTIVE' AND category = ?
            ORDER BY created_at DESC
            LIMIT 15;
        """, (h_id, cat))
        cursor.fetchall()
        latencies.append((time.perf_counter() - t_start) * 1000)
    benchmark_results["Household Memory Retrieval"] = latencies

    # 10. AI Context Construction (Multi-table snapshot aggregation)
    latencies = []
    for k in range(NUM_ITERS):
        h_id = home_ids[k * 37 % NUM_HOMES]
        t_start = time.perf_counter()
        cursor.execute("SELECT id, name, currency FROM homes WHERE id = ?;", (h_id,))
        cursor.fetchone()
        cursor.execute("SELECT id, title, due_date FROM tasks WHERE home_id = ? AND status = 'TODO' LIMIT 10;", (h_id,))
        cursor.fetchall()
        cursor.execute("SELECT id, name, is_low_stock FROM inventory_items WHERE home_id = ? AND is_low_stock = 1 LIMIT 10;", (h_id,))
        cursor.fetchall()
        cursor.execute("SELECT id, content FROM household_memories WHERE home_id = ? AND status = 'ACTIVE' LIMIT 8;", (h_id,))
        cursor.fetchall()
        latencies.append((time.perf_counter() - t_start) * 1000)
    benchmark_results["AI Context Construction"] = latencies

    conn.close()
    if os.path.exists(db_path):
        os.remove(db_path)

    # Format Summary Table
    print("\n| Operation | p50 (ms) | p95 (ms) | p99 (ms) | Max (ms) | Target Met |")
    print("|---|---|---|---|---|---|")
    output_dict = {}
    for op, times in benchmark_results.items():
        p50 = float(percentile(times, 50))
        p95 = float(percentile(times, 95))
        p99 = float(percentile(times, 99))
        max_v = float(max(times))
        met = "✅ PASS (<50ms)" if p95 < 50.0 else "⚠️ REVIEW"
        print(f"| **{op}** | {p50:.2f} ms | {p95:.2f} ms | {p99:.2f} ms | {max_v:.2f} ms | {met} |")
        output_dict[op] = {"p50": round(p50, 3), "p95": round(p95, 3), "p99": round(p99, 3), "max": round(max_v, 3)}


    with open("/tmp/ozhzo_benchmark_results.json", "w") as f:
        json.dump(output_dict, f, indent=2)

    print("\nBenchmark results written to /tmp/ozhzo_benchmark_results.json.")

if __name__ == "__main__":
    run_performance_benchmark()
