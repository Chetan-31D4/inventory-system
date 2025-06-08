import sqlite3

conn = sqlite3.connect('inventory.db')
c    = conn.cursor()

# Check which columns already exist in request_history:
c.execute("PRAGMA table_info(request_history)")
cols = [row[1] for row in c.fetchall()]
print("Before ALTER, columns in request_history:", cols)

if 'username' not in cols:
    # Add the new username column (default to an empty string for old rows):
    c.execute("ALTER TABLE request_history ADD COLUMN username TEXT DEFAULT ''")
    print("✨ Added 'username' column to request_history.")
else:
    print("ℹ️ 'username' column already exists; nothing to do.")

conn.commit()
conn.close()
