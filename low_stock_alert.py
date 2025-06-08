#!/usr/bin/env python3
import os
from datetime import datetime
import psycopg2
import psycopg2.extras

from flask import Flask
from flask_mail import Mail, Message

# ───────────────────────────────────────────────────────────────────────────────
#  A) Bootstrap a minimal Flask context so we can reuse the same Mail settings
# ───────────────────────────────────────────────────────────────────────────────
#
# We create a bare‐bones Flask app here with the same MAIL_ config as in your main
# application. Then we initialize Flask-Mail. That way we can call mail.send(...) below.

app = Flask(__name__)

# ── Copy your Flask‐Mail configuration from app.py ──
app.config['MAIL_SERVER']      = 'smtp.gmail.com'
app.config['MAIL_PORT']        = 587
app.config['MAIL_USE_TLS']     = True
app.config['MAIL_USERNAME']    = 'chetansinghal.fin@gmail.com'
app.config['MAIL_PASSWORD']    = 'ogjz xgug kbwy sfry'
app.config['MAIL_DEFAULT_SENDER'] = ('Inventory System', 'no-reply@mydomain.com')

mail = Mail(app)

# ───────────────────────────────────────────────────────────────────────────────
#  B) PostgreSQL connection parameters (same as in app.py)
# ───────────────────────────────────────────────────────────────────────────────
DB_USER = os.environ.get('PG_USER', 'inv_user')
DB_PASS = os.environ.get('PG_PASS', 'inv_pass123')
DB_HOST = os.environ.get('PG_HOST', 'localhost')
DB_PORT = os.environ.get('PG_PORT', '5432')
DB_NAME = os.environ.get('PG_DB',   'inventorydb')

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def get_db_cursor():
    """
    Returns (conn, cur) where cur is a RealDictCursor.
    Caller must call conn.close() after use.
    """
    conn = psycopg2.connect(DATABASE_URL)
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    return conn, cur

# ───────────────────────────────────────────────────────────────────────────────
#  C) “Daily low‐stock check” logic
# ───────────────────────────────────────────────────────────────────────────────
def send_low_stock_report():
    with app.app_context():
        # 1) Fetch all products whose quantity < reorder_level
        conn, cur = get_db_cursor()
        cur.execute("""
            SELECT id, name, quantity, reorder_level
            FROM products
            WHERE quantity < reorder_level
            ORDER BY (reorder_level - quantity) DESC
        """)
        low_products = cur.fetchall()
        conn.close()

        if not low_products:
            # Nothing to report today
            print(f"[{datetime.now().isoformat()}] No low‐stock items found.")
            return

        # 2) Gather all admin email addresses
        conn, cur = get_db_cursor()
        cur.execute("SELECT email FROM users WHERE role = 'admin' AND email IS NOT NULL")
        admin_rows = cur.fetchall()
        conn.close()

        admin_emails = [r['email'] for r in admin_rows if r.get('email')]
        if not admin_emails:
            print(f"[{datetime.now().isoformat()}] No admin emails configured – skipping.")
            return

        # 3) Build email body
        lines = [
            "Hello Admin,\n",
            "The following products are below their reorder point:\n"
        ]
        for prod in low_products:
            lines.append(
                f"  • {prod['name']} (ID #{prod['id']}): "
                f"{prod['quantity']} left  |  threshold = {prod['reorder_level']}\n"
            )
        lines.append("\nPlease consider replenishing inventory as needed.\n\n")
        lines.append("— Inventory System")

        subject = "⚠️ Daily Low‐Stock Alert"
        body_text = "".join(lines)

        # 4) Send one email to all admins (To: list of admin_emails; you can Bcc or send individually if you prefer)
        msg = Message(subject=subject, recipients=admin_emails)
        msg.body = body_text
        try:
            mail.send(msg)
            print(f"[{datetime.now().isoformat()}] Low‐stock email sent to: {', '.join(admin_emails)}")
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] ERROR sending low‐stock email: {e}")


if __name__ == "__main__":
    send_low_stock_report()
