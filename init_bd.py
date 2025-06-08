import sqlite3

conn = sqlite3.connect('inventory.db')
c = conn.cursor()

# Create products table if it doesn't exist
c.execute('''
CREATE TABLE IF NOT EXISTS products (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name     TEXT NOT NULL,
    type     TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    price    REAL NOT NULL DEFAULT 0.0
)
''')


# Create users table with role support
c.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'viewer'))
)
''')

c.execute('''
CREATE TABLE IF NOT EXISTS edit_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    requested_name TEXT NOT NULL,
    requested_type TEXT NOT NULL,
    requested_quantity INTEGER NOT NULL,
    requested_by TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (requested_by) REFERENCES users(username)
)
''')

c.execute('''
CREATE TABLE IF NOT EXISTS request_history (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    username       TEXT NOT NULL,
    product_id     INTEGER NOT NULL,
    product_name   TEXT NOT NULL,
    quantity       INTEGER NOT NULL,         -- approved quantity
    reason         TEXT NOT NULL,
    sub_reason     TEXT,
    drone_number   TEXT NOT NULL,
    status         TEXT NOT NULL,            -- 'pending', 'approved', 'rejected'
    requested_at   TEXT NOT NULL,
    decision_at    TEXT,
    decided_by     TEXT,
    used           INTEGER NOT NULL DEFAULT 0,
    remaining      INTEGER NOT NULL DEFAULT 0,
    gst_exclusive  REAL NOT NULL DEFAULT 0.0,  -- NEW: price × quantity
    total_inclusive REAL NOT NULL DEFAULT 0.0  -- NEW: gst_exclusive × 1.18
)
''')



c.execute('''
CREATE TABLE IF NOT EXISTS stock_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    product_name TEXT,
    changed_by TEXT,
    old_quantity INTEGER,
    new_quantity INTEGER,
    change_amount INTEGER,
    changed_at TEXT
)
''')


c.execute('''
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,           -- <— NEW COLUMN
    reason TEXT NOT NULL,
    sub_reason TEXT,
    drone_number TEXT NOT NULL,
    status TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    FOREIGN KEY(username) REFERENCES users(username),
    FOREIGN KEY(product_id) REFERENCES products(id)
)
''')



# Insert sample product
# c.execute("INSERT OR IGNORE INTO products (id, name, quantity) VALUES (1, 'Test product', 10)")

# Insert admin users
c.execute("INSERT OR IGNORE INTO users (id, username, password, role) VALUES (1, 'Chetan_Singhal', 'Chetan@1002', 'admin')")
c.execute("INSERT OR IGNORE INTO users (id, username, password, role) VALUES (2, 'Pulkit', 'Pulkit_Mittal', 'admin')")
c.execute("INSERT OR IGNORE INTO users (id, username, password, role) VALUES (3, 'Karthik', 'Karthik@1234', 'admin')")

# Insert viewer users
viewer_users = [
    ('viewer1', 'viewpass1', 'viewer'),
    ('viewer2', 'viewpass2', 'viewer'),
    ('viewer3', 'viewpass3', 'viewer'),
    ('viewer4', 'viewpass4', 'viewer'),
    ('viewer5', 'viewpass5', 'viewer'),
]

for i, (username, password, role) in enumerate(viewer_users, start=3):
    c.execute("INSERT OR IGNORE INTO users (id, username, password, role) VALUES (?, ?, ?, ?)",
              (i, username, password, role))

conn.commit()
conn.close()

print("Database initialized with 3 admins and 5 viewers.")