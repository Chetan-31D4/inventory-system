import os
import pandas as pd
from flask     import Flask, render_template, request, redirect, url_for, session, flash, send_file
from io        import BytesIO
from datetime  import datetime
from zoneinfo  import ZoneInfo
from datetime import datetime
import psycopg2
import psycopg2.extras
from flask_mail import Mail, Message

from flask import Flask, render_template, session, redirect, url_for
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

app = Flask(__name__)
app.secret_key = os.urandom(24)

app.config['MAIL_SERVER']        = 'smtp.gmail.com'
app.config['MAIL_PORT']          = 587
app.config['MAIL_USE_TLS']       = True
app.config['MAIL_USERNAME']      = 'chetansinghal.fin@gmail.com'
app.config['MAIL_PASSWORD']      = 'ogjz xgug kbwy sfry'
app.config['MAIL_DEFAULT_SENDER']= ('Inventory System', 'no-reply@mydomain.com')

mail = Mail(app)

# PostgreSQL connection parameters (adjust as needed or via environment variables)
DB_USER = os.environ.get('PG_USER', 'inv_user')
DB_PASS = os.environ.get('PG_PASS', 'inv_pass123')
DB_HOST = os.environ.get('PG_HOST', 'localhost')
DB_PORT = os.environ.get('PG_PORT', '5432')
DB_NAME = os.environ.get('PG_DB',   'inventorydb')

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


def get_db():
    """
    Opens a new connection to PostgreSQL (using DATABASE_URL) and returns it.
    The cursor_factory is set to RealDictCursor, so row fetches return dict-like objects.
    """
    conn = psycopg2.connect(DATABASE_URL)
    # Ensure that subsequent .cursor() calls return RealDictCursor by default:
    conn.cursor_factory = psycopg2.extras.RealDictCursor
    return conn


# ────────────────────────────────────────────────────────────────────
# 2.b) get_db_cursor(): convenience function to get (conn, cur) at once
#                      with RealDictCursor
# ────────────────────────────────────────────────────────────────────
def get_db_cursor():
    """
    Returns a tuple (conn, cur) where:
      - conn is a new psycopg2 connection (RealDictCursor by default)
      - cur  is conn.cursor(), so it yields rows as dictionaries.
    Caller is responsible for conn.commit() and conn.close() when done.
    """
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    return conn, cur

@app.route('/contact')
def contact_us():
    # Only viewers should see it:
    if 'username' not in session or session.get('role') != 'viewer':
        return "Unauthorized", 403

    last_updated = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return render_template('contact_us.html', last_updated=last_updated)

# @app.route('/')
# def dashboard():
#     if 'username' not in session:
#         return redirect(url_for('login'))

#     conn = get_db()
#     c = conn.cursor()
#     c.execute("SELECT * FROM products")
#     products = c.fetchall()

#     edit_requests = []
#     if session.get('role') == 'admin':
#         # OLD:
#         # c.execute("SELECT * FROM edit_requests WHERE status='pending'")
#         # edit_requests = c.fetchall()

#         # NEW:
#         c.execute("SELECT * FROM request_history WHERE status='pending' ORDER BY requested_at DESC")
#         edit_requests = c.fetchall()

#     conn.close()
#     return render_template('dashboard.html', products=products, role=session.get('role'), edit_requests=edit_requests)


# inside app.py (or wherever you defined dashboard)
from flask import request  # make sure this is already imported

@app.route('/')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    # 1) grab the 'search' parameter (GET)
    search_term = request.args.get('search', '').strip()

    conn, cur = get_db_cursor()
    if search_term:
        # Use ILIKE for case‐insensitive match in PostgreSQL
        cur.execute("""
            SELECT *
              FROM products
             WHERE name ILIKE %s
             ORDER BY id
        """, (f'%{search_term}%',))
    else:
        cur.execute("SELECT * FROM products ORDER BY id")
    products = cur.fetchall()
    conn.close()

    # 2) If admin, fetch pending requests exactly as before
    edit_requests = []
    if session.get('role') == 'admin':
        conn2, cur2 = get_db_cursor()
        cur2.execute("""
            SELECT *
              FROM request_history
             WHERE status = 'pending'
             ORDER BY requested_at DESC
        """)
        edit_requests = cur2.fetchall()
        conn2.close()

    # 3) Pass 'search_term' back to template so the input can show it
    return render_template(
        'dashboard.html',
        products=products,
        role=session.get('role'),
        edit_requests=edit_requests,
        search=search_term
    )


@app.route('/add', methods=['POST'])
def add_product():
    if session.get('role') != 'admin':
        return "Unauthorized", 403
    name = request.form['name']
    type_ = request.form['type']
    quantity = request.form['quantity']
    conn = get_db()
    c = conn.cursor()
    c.execute('INSERT INTO products (name, type, quantity) VALUES (%s,%s,%s)', (name,type_,quantity))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

def send_low_stock_alert_if_needed(product_id, new_quantity):
    """
    If new_quantity < reorder_level, fetch all admin emails and send an alert.
    """
    conn, cur = get_db_cursor()
    # 1) Fetch reorder_level and name
    cur.execute(
        "SELECT name, reorder_level FROM products WHERE id = %s",
        (product_id,)
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return

    name         = row['name']
    reorder_lvl  = row['reorder_level']

    if new_quantity < reorder_lvl:
        # 2) Fetch all admin emails
        conn, cur = get_db_cursor()
        cur.execute("SELECT email FROM users WHERE role = 'admin' AND email IS NOT NULL")
        admins = cur.fetchall()
        conn.close()

        admin_emails = [r['email'] for r in admins if r.get('email')]
        if not admin_emails:
            return

        # 3) Compose and send the email
        msg = Message(
            subject=f"[ALERT] Low stock: {name}",
            recipients=admin_emails
        )
        msg.body = (
            f"Attention Inventory Admins,\n\n"
            f"The product “{name}” (ID {product_id}) has fallen below its reorder level ({reorder_lvl}).\n"
            f"Current quantity is {new_quantity}.\n\n"
            "Please consider re‐ordering soon.\n\n"
            "– Inventory System"
        )
        mail.send(msg)


@app.route('/edit/<int:id>', methods=['POST'])
def edit_product(id):
    if session.get('role') != 'admin':
        return "Unauthorized", 403

    name = request.form['name']
    type_ = request.form['type']
    new_quantity = int(request.form['quantity'])

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT * FROM products WHERE id = %s", (id,))
    product = c.fetchone()

    if not product:
        conn.close()
        flash("Product not found.", "error")
        return redirect(url_for('dashboard'))

    old_quantity = product['quantity']
    change_amount = new_quantity - old_quantity

    # Update product
    c.execute('UPDATE products SET name = %s, type = %s, quantity = %s WHERE id = %s', 
              (name, type_, new_quantity, id))

    # Log to stock_history
    from datetime import datetime
    from zoneinfo import ZoneInfo
    changed_at = datetime.now(ZoneInfo("Asia/Kolkata")).strftime('%Y-%m-%d %H:%M:%S')

    c.execute('''
        INSERT INTO stock_history (
            product_id, product_name, changed_by, old_quantity, new_quantity, change_amount, changed_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
    ''', (id, name, session['username'], old_quantity, new_quantity, change_amount, changed_at))

    conn.commit()
    conn.close()
    flash("Product updated and change logged.", "success")
    return redirect(url_for('dashboard'))



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # conn = sqlite3.connect('inventory.db')
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, password))
        user = c.fetchone()
        conn.close()

        if user:
            session['username'] = user['username']
            session['role'] = user['role']  # 'admin' or 'viewer'
            return redirect(url_for('dashboard'))
        else:
            return "Invalid credentials"
    return render_template('login.html')


from datetime import datetime
from zoneinfo import ZoneInfo  # Requires Python 3.9+

@app.route('/request_edit/<int:id>', methods=['POST'])
def request_edit(id):
    if session.get('role') != 'viewer':
        return "Unauthorized", 403

    requested_quantity = int(request.form['requested_quantity'])
    requested_by = session['username']

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT * FROM products WHERE id = %s", (id,))
    product = c.fetchone()

    if product is None:
        conn.close()
        flash("Product not found.", "error")
        return redirect(url_for('dashboard'))

    if requested_quantity > product['quantity']:
        conn.close()
        flash("Requested quantity exceeds available stock.", "error")
        return redirect(url_for('dashboard'))

    # Get current time in desired timezone (e.g., Asia/Kolkata)
    requested_at = datetime.now(ZoneInfo("Asia/Kolkata")).strftime('%Y-%m-%d %H:%M:%S')

    # Insert into request_history with requested_at
    c.execute('''
        INSERT INTO request_history (
            product_id, product_name, requested_quantity, requested_by, status, requested_at
        ) VALUES (%s, %s, %s, %s, 'pending', %s)
    ''', (id, product['name'], requested_quantity, requested_by, requested_at))

    conn.commit()
    conn.close()

    flash("Item request submitted to admin.", "info")
    return redirect(url_for('dashboard'))

from datetime import datetime
from zoneinfo import ZoneInfo  # Python 3.9+

from datetime import datetime
from zoneinfo import ZoneInfo


@app.route('/approve_request/<int:request_id>', methods=['GET', 'POST'])
def approve_request(request_id):
    if session.get('role') != 'admin':
        return "Unauthorized", 403

    # 1) Fetch the pending request from request_history
    conn, cur = get_db_cursor()
    cur.execute("SELECT * FROM request_history WHERE id = %s", (request_id,))
    req = cur.fetchone()
    conn.close()

    if not req or req['status'] != 'pending':
        # Either no such request or it's already handled
        flash("Request not found or already handled.", "error")
        return redirect(url_for('dashboard'))

    # ─────────────── GET: Show the "Approve" form with comment box ───────────────
    if request.method == 'GET':
        return render_template(
            'approve_request.html',
            req_id          = request_id,
            product_name    = req['product_name'],
            requested_qty   = req['quantity'],
            current_comment = req.get('comment', '') or ''
        )

    # ─────────────── POST: Process the approval ───────────────
    admin_comment = request.form.get('admin_comment', '').strip()

    # 2) Re‐fetch product to check stock
    conn, cur = get_db_cursor()
    cur.execute("SELECT * FROM products WHERE id = %s", (req['product_id'],))
    product = cur.fetchone()

    if not product or product['quantity'] < req['quantity']:
        conn.close()
        flash("Insufficient stock to approve this request.", "error")
        return redirect(url_for('dashboard'))

    # 3) Deduct inventory
    new_qty = product['quantity'] - req['quantity']
    cur.execute(
        "UPDATE products SET quantity = %s WHERE id = %s",
        (new_qty, req['product_id'])
    )

    # 4) Compute GST amounts
    approved_qty    = req['quantity']
    price_per_item  = product['price']   # assumes a "price" column on products
    gst_exclusive   = price_per_item * approved_qty
    total_inclusive = round(gst_exclusive * 1.18, 2)

    decision_at_str = datetime.now(ZoneInfo("Asia/Kolkata")).strftime('%Y-%m-%d %H:%M:%S')

    # 5) Update request_history, including the admin's comment
    cur.execute(
        """
        UPDATE request_history
        SET 
            status          = 'approved',
            decision_at     = %s,
            decided_by      = %s,
            used            = 0,
            remaining       = quantity,
            gst_exclusive   = %s,
            total_inclusive = %s,
            comment         = %s
        WHERE id = %s
        """,
        (
            decision_at_str,
            session['username'],   # admin's username
            gst_exclusive,
            total_inclusive,
            admin_comment,
            request_id
        )
    )
    conn.commit()
    conn.close()

    # 6) Send email to the requesting viewer (if they have an email on file)
    try:
        conn, cur = get_db_cursor()
        viewer_username = req['username']
        cur.execute("SELECT email FROM users WHERE username = %s", (viewer_username,))
        viewer_row = cur.fetchone()
        conn.close()

        if viewer_row and viewer_row.get('email'):
            viewer_email = viewer_row['email']
            msg = Message(
                subject=f"Your request #{request_id} has been APPROVED",
                recipients=[viewer_email]
            )
            msg.body = (
                f"Hello {viewer_username},\n\n"
                f"Your request for {approved_qty} × {req['product_name']} has been *APPROVED*.\n"
                f"  • Approved quantity: {approved_qty}\n"
                f"  • GST‐exclusive amount: ₹{gst_exclusive:.2f}\n"
                f"  • Total (incl. 18% GST): ₹{total_inclusive:.2f}\n"
                f"  • Admin comment: {admin_comment or '—'}\n\n"
                "Thank you,\nInventory Team"
            )
            mail.send(msg)
    except Exception as e:
        flash(f"⚠️ Could not send approval email to {viewer_username}: {e}", "warning")

    flash("Request approved, stock updated, and email sent to viewer.", "success")
    return redirect(url_for('dashboard'))





@app.route('/reject_request/<int:request_id>', methods=['GET', 'POST'])
def reject_request(request_id):
    if session.get('role') != 'admin':
        return "Unauthorized", 403

    # 1) Fetch the pending request
    conn, cur = get_db_cursor()
    cur.execute("SELECT * FROM request_history WHERE id = %s", (request_id,))
    req = cur.fetchone()
    conn.close()

    if not req or req['status'] != 'pending':
        flash("Request not found or already handled.", "error")
        return redirect(url_for('dashboard'))

    # ─────────────── GET: Show the "Reject" form with comment box ───────────────
    if request.method == 'GET':
        return render_template(
            'reject_request.html',
            req_id          = request_id,
            product_name    = req['product_name'],
            requested_qty   = req['quantity'],
            current_comment = req.get('comment', '') or ''
        )

    # ─────────────── POST: Process the rejection ───────────────
    admin_comment   = request.form.get('admin_comment', '').strip()
    decision_at_str = datetime.now(ZoneInfo("Asia/Kolkata")).strftime('%Y-%m-%d %H:%M:%S')

    conn, cur = get_db_cursor()
    cur.execute(
        """
        UPDATE request_history
        SET 
            status      = 'rejected',
            decision_at = %s,
            decided_by  = %s,
            comment     = %s
        WHERE id = %s
        """,
        (
            decision_at_str,
            session['username'],  # admin’s username
            admin_comment,
            request_id
        )
    )
    conn.commit()
    conn.close()

    # Send rejection email to the viewer, if available
    try:
        conn, cur = get_db_cursor()
        viewer_username = req['username']
        cur.execute("SELECT email FROM users WHERE username = %s", (viewer_username,))
        viewer_row = cur.fetchone()
        conn.close()

        if viewer_row and viewer_row.get('email'):
            viewer_email = viewer_row['email']
            msg = Message(
                subject=f"Your request #{request_id} has been REJECTED",
                recipients=[viewer_email]
            )
            msg.body = (
                f"Hello {viewer_username},\n\n"
                f"Your request for {req['quantity']} × {req['product_name']} has been *REJECTED*.\n"
                f"  • Admin comment: {admin_comment or '—'}\n\n"
                "Please contact the inventory team if you have questions.\n\n"
                "Regards,\nInventory System"
            )
            mail.send(msg)
    except Exception as e:
        flash(f"⚠️ Could not send rejection email to {viewer_username}: {e}", "warning")

    flash("Request rejected, comment saved, and email sent to viewer.", "info")
    return redirect(url_for('dashboard'))



@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'info')
    return redirect(url_for('login'))



@app.route('/history')
def viewer_history():
    if 'username' not in session:
        return redirect(url_for('login'))

    conn, cur = get_db_cursor()
    if session['role'] == 'viewer':
        cur.execute('''
            SELECT *
            FROM request_history
            WHERE username = %s
            ORDER BY requested_at DESC
        ''', (session['username'],))
    else:
        cur.execute('''
            SELECT *
            FROM request_history
            ORDER BY requested_at DESC
        ''')

    history_rows = cur.fetchall()
    conn.close()
    return render_template('history.html', history=history_rows)



@app.route('/api/pending_requests')
def get_pending_requests():
    if session.get('role') != 'admin':
        return "Forbidden", 403

    conn, cur = get_db_cursor()
    cur.execute('''
        SELECT
          id,
          product_id,
          product_name,
          quantity,
          reason,
          sub_reason,
          drone_number,
          username AS requested_by,
          requested_at
        FROM request_history
        WHERE status = 'pending'
        ORDER BY requested_at DESC
    ''')
    rows = cur.fetchall()
    conn.close()

    result = []
    for r in rows:
        # r['requested_at'] is a datetime, convert to string
        requested_at_str = r['requested_at'].strftime('%Y-%m-%d %H:%M:%S')
        result.append({
            "id":                 r["id"],
            "product_id":         r["product_id"],
            "product_name":       r["product_name"],
            "requested_quantity": r["quantity"],       # ← changed key from "quantity" to "requested_quantity"
            "reason":             r["reason"],
            "sub_reason":         r["sub_reason"],
            "drone_number":       r["drone_number"],
            "requested_by":       r["requested_by"],
            "requested_at":       requested_at_str
        })
    return {"requests": result}


@app.route('/api/download-filtered-excel', methods=['POST'])
def download_filtered_excel():
    if 'username' not in session or session.get('role') != 'admin':
        return "Unauthorized", 403

    data = request.json.get('data', [])

    if not data:
        return "No data provided", 400

    # Define column names matching the 13‐column order sent from JS:
    columns = [
        'ID',
        'Product',
        'Qty',
        'Reason',
        'Sub Reason',
        'Drone No.',
        'Status',
        'Requested At',
        'Decision At',
        'Admin',
        'Requested By',
        'Used',
        'Remaining'
    ]

    # Create DataFrame with those columns
    df = pd.DataFrame(data, columns=columns)

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Filtered History')

    output.seek(0)
    return send_file(
        output,
        download_name="filtered_request_history.xlsx",
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


@app.route('/stock_history')
def stock_history():
    if session.get('role') != 'admin':
        return "Unauthorized", 403

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM stock_history ORDER BY changed_at DESC")
    history = c.fetchall()
    conn.close()
    return render_template('stock_history.html', history=history)


@app.route('/download_stock_history')
def download_stock_history():
    if session.get('role') != 'admin':
        return "Unauthorized", 403

    keyword = request.args.get('q', '').strip()

    conn = get_db()
    c = conn.cursor()

    if keyword:
        c.execute('''
            SELECT * FROM stock_history
            WHERE product_name LIKE %s
            ORDER BY changed_at DESC
        ''', (f'%{keyword}%',))
    else:
        c.execute("SELECT * FROM stock_history ORDER BY changed_at DESC")

    rows = c.fetchall()
    conn.close()

    df = pd.DataFrame(rows, columns=[desc[0] for desc in c.description])

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    return send_file(output, as_attachment=True, download_name="stock_history.xlsx", mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if session.get('role') != 'viewer':
        return "Unauthorized", 403

    # 1. Read the new quantity field from the form:
    try:
        requested_qty = int(request.form['quantity'])
        if requested_qty < 1:
            raise ValueError()
    except (KeyError, ValueError):
        flash("Please provide a valid quantity (1 or more).", "error")
        return redirect(url_for('dashboard'))

    product_id = int(request.form['product_id'])
    reason = request.form['reason']
    sub_reason = request.form.get('sub_reason', '')
    drone_number = request.form['drone_number']

    if not reason or not drone_number:
        flash("Reason and Drone Number are required.", "error")
        return redirect(url_for('dashboard'))

    # Initialize cart
    if 'cart' not in session:
        session['cart'] = []

    # Prevent duplicates (same product_id) – you could also allow duplicates if you prefer
    for item in session['cart']:
        if item['product_id'] == product_id:
            flash("This item is already in your cart.", "warning")
            return redirect(url_for('dashboard'))

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT name FROM products WHERE id = %s", (product_id,))
    result = c.fetchone()
    conn.close()

    if not result:
        flash("Product not found.", "error")
        return redirect(url_for('dashboard'))

    product_name = result['name']

    # Add to cart, including the quantity
    session['cart'].append({
        'product_id': product_id,
        'product_name': product_name,
        'quantity': requested_qty,      # <— NEW FIELD
        'reason': reason,
        'sub_reason': sub_reason,
        'drone_number': drone_number
    })

    session.modified = True
    flash("Item added to cart.", "success")
    return redirect(url_for('dashboard'))


@app.route('/view_cart')
def view_cart():
    if 'username' not in session or session.get('role') != 'viewer':
        return "Unauthorized", 403

    cart = session.get('cart', [])
    return render_template('view_cart.html', cart=cart)



@app.route('/submit_cart', methods=['POST'])
def submit_cart():
    if 'username' not in session or session.get('role') != 'viewer':
        return "Unauthorized", 403

    cart = session.get('cart', [])
    if not cart:
        flash("Your cart is empty.", "error")
        return redirect(url_for('view_cart'))

    username  = session['username']
    timestamp = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")

    # 1) Insert each item into request_history (status = 'pending')
    conn, cur = get_db_cursor()
    for item in cart:
        cur.execute('''
            INSERT INTO request_history
            (username,
             product_id,
             product_name,
             quantity,
             reason,
             sub_reason,
             drone_number,
             status,
             requested_at,
             comment)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending', %s, '')
        ''', (
            username,
            item['product_id'],
            item['product_name'],
            item['quantity'],
            item['reason'],
            item['sub_reason'],
            item['drone_number'],
            timestamp
        ))
    conn.commit()
    conn.close()

    # 2) Email notification to all admins
    try:
        conn, cur = get_db_cursor()
        cur.execute("SELECT email FROM users WHERE role = 'admin'")
        admins = cur.fetchall()  # list of dicts, each with key 'email'
        conn.close()

        admin_emails = [row['email'] for row in admins]
        if admin_emails:
            lines = [f"User {username} has submitted these requests:"]
            for item in cart:
                lines.append(
                    f"  • {item['quantity']} × {item['product_name']} "
                    f"(Reason: {item['reason'] or '—'}, Drone: {item['drone_number']})"
                )
            body_text = "\n".join(lines)

            msg = Message(
                subject=f"New Inventory Request from {username}",
                recipients=admin_emails
            )
            msg.body = body_text
            mail.send(msg)
    except Exception as e:
        flash(f"⚠️ Could not send notification email to admins: {e}", "warning")

    # 3) Clear cart & redirect
    session['cart'] = []
    flash("All requests submitted successfully! The admin has been notified.", "success")
    return redirect(url_for('dashboard'))



@app.route('/edit_usage/<int:request_id>', methods=['GET', 'POST'])
def edit_usage(request_id):
    # 1) Only logged-in viewers can access this
    if 'username' not in session or session.get('role') != 'viewer':
        return "Unauthorized", 403

    conn = get_db()
    c = conn.cursor()

    # 2) Fetch that specific request row
    c.execute("SELECT * FROM request_history WHERE id = %s", (request_id,))
    req = c.fetchone()

    # 3) Validate that it exists, belongs to the current viewer, and is approved
    if not req or req['username'] != session['username'] or req['status'] != 'approved':
        conn.close()
        flash("You cannot update usage for this request.", "error")
        return redirect(url_for('viewer_history'))  # or 'history'

    # If it’s a GET request, show the form
    if request.method == 'GET':
        conn.close()
        return render_template(
            'edit_usage.html',
            req_id=req['id'],
            used=req['used'],
            remaining=req['remaining'],
            approved_qty=req['quantity']
        )

    # Otherwise, it’s a POST → process the form submission
    try:
        used = int(request.form['used'])
        remaining = int(request.form['remaining'])
    except (KeyError, ValueError):
        flash("Please enter valid integer values.", "error")
        conn.close()
        return redirect(url_for('edit_usage', request_id=request_id))

    # Enforce that used + remaining === approved quantity
    approved_qty = req['quantity']
    if used < 0 or remaining < 0 or (used + remaining) != approved_qty:
        flash("Used + Remaining must exactly equal the approved quantity.", "error")
        conn.close()
        return redirect(url_for('edit_usage', request_id=request_id))

    # Update the row
    c.execute(
        "UPDATE request_history SET used = %s, remaining = %s WHERE id = %s",
        (used, remaining, request_id)
    )
    conn.commit()
    conn.close()

    flash("Usage updated successfully.", "success")
    return redirect(url_for('viewer_history'))

@app.route('/test-email')
def test_email():
    """
    A quick route to verify your SMTP setup. Visit /test-email in browser.
    """
    try:
        msg = Message(
            subject    = "Test Email from Flask",
            recipients = ["chetanaggarwal21123@gmail.com"]
        )
        msg.body = "If you see this, SMTP is working!"
        mail.send(msg)
        return "✓ Email sent (check your inbox)."
    except Exception as e:
        return f"Error sending email: {e}"

@app.route('/analytics')
def analytics():
    # Only admins can view analytics
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('dashboard'))

    # ─── 1) Top 10 Most Requested Items (Last 30 days) ───
    conn, cur = get_db_cursor()

    # Compute the "30 days ago" cutoff in Asia/Kolkata
    thirty_days_ago = (datetime.now(ZoneInfo("Asia/Kolkata")) - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')

    # Sum up approved quantities per product_name in the last 30 days
    cur.execute("""
        SELECT
          product_name,
          SUM(quantity) AS total_requested
        FROM request_history
        WHERE status = 'approved'
          AND decision_at::timestamp >= %s
        GROUP BY product_name
        ORDER BY total_requested DESC
        LIMIT 10
    """, (thirty_days_ago,))
    top_rows = cur.fetchall()
    conn.close()

    top_requested = [
        { 'product_name': r['product_name'], 'total_requested': int(r['total_requested']) }
        for r in top_rows
    ]

    # ─── 2) Daily Approved Quantity (Last 30 days) ───
    # First initialize a dict for each of the last 30 calendar dates (YYYY-MM-DD) → 0
    daily_counts = {}
    today_date = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    for i in range(30):
        day = today_date - timedelta(days=29 - i)
        daily_counts[day.isoformat()] = 0

    # Now fetch actual sums, grouping by the “date” portion of decision_at (shifted into Asia/Kolkata)
    conn, cur = get_db_cursor()
    cur.execute("""
        SELECT
          DATE( (decision_at::timestamp) AT TIME ZONE 'Asia/Kolkata' ) AS day_date,
          SUM(quantity) AS daily_approved
        FROM request_history
        WHERE status = 'approved'
          AND decision_at::timestamp >= %s
        GROUP BY day_date
        ORDER BY day_date
    """, (thirty_days_ago,))
    trend_rows = cur.fetchall()
    conn.close()

    for tr in trend_rows:
        day_str = tr['day_date'].isoformat()        # e.g. '2025-05-10'
        if day_str in daily_counts:
            daily_counts[day_str] = int(tr['daily_approved'])

    # Build a list of dicts in date order:
    usage_trend = [
        { 'day_date': date_str, 'daily_approved': qty }
        for date_str, qty in daily_counts.items()
    ]

    # ─── 3) Render template with both lists ───
    return render_template(
        'analytics.html',
        top_requested=top_requested,
        usage_trend=usage_trend
    )


if __name__ == '__main__':
    # Render (and other PaaS) will set the PORT env var
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)