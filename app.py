from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_bcrypt import Bcrypt
import smtplib
import os
import re
from email.header import decode_header
import imaplib
import email



app = Flask(__name__)
app.secret_key = os.urandom(24)

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://postgres:Suprathika@localhost:5432/DB"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Extensions
db = SQLAlchemy(app)
CORS(app)
bcrypt = Bcrypt(app)

# Email Credentials
EMAIL_ADDRESS = "suprathikaramisetty@gmail.com"
EMAIL_PASSWORD = "tmoz pbmr jmlm cfyj"  # App password, not real password

# Database Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # Add this line

    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

# Routes
@app.route('/email')
def home():
    return render_template("email.html")
@app.route('/')
def home4():
    return render_template("login.html")

@app.route('/trash')
def home1():
    return render_template("trash.html")
@app.route('/sent')
def home2():
    return render_template("sent.html")
@app.route('/logout')
def home3():
    return render_template("register.html")


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password'].strip()

        user = User.query.filter_by(email=email).first()

        if user and bcrypt.check_password_hash(user.password, password):
            flash('Login successful')
            return redirect(url_for('menu'))
        else:
            flash('Invalid email or password')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip().lower()
        password = request.form['password'].strip()

        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            flash('Email already registered. Please login.')
            return redirect(url_for('login'))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        new_user = User(name=name, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! You can now login.')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/menu')
def menu():
    return render_template("menu.html")
@app.route('/inbox')
def menu2():
    return render_template("inbox.html")

@app.route('/send-email', methods=['POST'])
def handle_send_email():
    data = request.get_json()
    recipient = data.get("email", "").strip()
    subject = data.get("subject", "").strip()
    message = data.get("message", "").strip()

    if not recipient or not subject or not message:
        return jsonify({"message": "Invalid email data."}), 400

    success = send_email(recipient, subject, message)
    if success:
        return jsonify({"message": "Email sent successfully!"})
    else:
        return jsonify({"message": "Failed to send email."}), 500


def send_email(recipient, subject, message):
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

            email_message = f"Subject: {subject}\n\n{message}"
            server.sendmail(EMAIL_ADDRESS, recipient, email_message)
            print(f"Email sent to {recipient}")
        return True
    except Exception as e:
        print("Error sending email:", e)
        return False
@app.route('/get-emails')
def get_emails():
    folder = request.args.get("folder", "INBOX")
    folder_map = {
        "inbox": "INBOX",
        "trash": "[Gmail]/Trash"
    }
    return jsonify(fetch_emails(folder_map.get(folder.lower(), "INBOX")))

def fetch_emails(folder="INBOX", limit=10):
    emails = []
    try:
        imap = imaplib.IMAP4_SSL("imap.gmail.com")
        imap.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        imap.select(folder)

        status, messages = imap.search(None, "ALL")
        if status != "OK":
            return []

        message_ids = messages[0].split()
        for msg_id in reversed(message_ids[-limit:]):
            _, msg_data = imap.fetch(msg_id, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])
            subject, encoding = decode_header(msg["Subject"])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding or "utf-8", errors='ignore')
            from_ = msg.get("From")

            emails.append({
                "subject": subject,
                "from": from_,
                "unread": True,
                "trashed": folder == "[Gmail]/Trash"
            })

        imap.logout()
    except Exception as e:
        print("IMAP error:", e)
    return emails



# Utility: extract email details from speech text (not used directly here)
def extract_email_details(command):
    pattern = r"send email to (.*?) subject (.*?) message (.*)"
    match = re.search(pattern, command, re.IGNORECASE)
    if match:
        recipient = match.group(1).strip()
        subject = match.group(2).strip()
        message = match.group(3).strip()
        return recipient, subject, message
    return None, None, None

# Main entry
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
