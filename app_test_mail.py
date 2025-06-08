# app_test_mail.py

from flask import Flask
from flask_mail import Mail, Message  # <-- make sure Flask-Mail is installed

app = Flask(__name__)
app.secret_key = 'efwjbfwofiefFIWBEFIUWFWFUIWFWIUFOHFEWOFHWOIFHWFWOIFHW'

# ────────────────────────────────────────────────────────────────────
# 1) Configure Flask-Mail with Gmail’s SMTP settings
#    (Adjust these if you use a different SMTP provider.)
# ────────────────────────────────────────────────────────────────────
app.config['MAIL_SERVER']        = 'smtp.gmail.com'
app.config['MAIL_PORT']          = 587
app.config['MAIL_USE_TLS']       = True
app.config['MAIL_USERNAME'] = 'chetansinghal.fin@gmail.com'
app.config['MAIL_PASSWORD'] = 'ogjz xgug kbwy sfry'   # an App Password, NOT your normal Gmail password
app.config['MAIL_DEFAULT_SENDER']= ('Inventory System', 'no-reply@mydomain.com')
# ────────────────────────────────────────────────────────────────────

# 2) Initialize the Mail object *after* you set app.config[...] above
mail = Mail(app)


# 3) A simple route to test sending an email
@app.route('/test-email')
def test_email():
    try:
        # Build a Message object
        msg = Message(
            subject="Test Email from Flask‐Mail",
            recipients=["chetanaggarwal21123@gmail.com"]  # send to yourself for testing
        )
        msg.body = "If you see this email, then your SMTP setup works!"
        mail.send(msg)
        return "✓ Email sent successfully! Check your inbox."
    except Exception as e:
        # Print the exception out in the browser so we can debug it
        return f"❌ Error sending email: {e}"


if __name__ == '__main__':
    app.run(debug=True)
