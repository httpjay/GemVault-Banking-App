import os 
from flask import Flask, request, make_response, redirect, render_template, g, flash, session
from user_service import get_user_with_credentials, logged_in, is_logged_in
from account_service import get_balance, do_transfer
from flask_wtf.csrf import CSRFProtect
from passlib.hash import pbkdf2_sha256
import sqlite3
import jwt
from datetime import datetime, timedelta
from user_service import SECRET
from flask_mail import Mail, Message
from account_service import get_balance
import pyotp
import random


# ✅ Initialize Flask app and mail config for MFA and password recovery
app = Flask(__name__)

# ✅ Then configure it
app.config['SECRET_KEY'] = 'mysecret123'
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'shivanilookup@gmail.com'
app.config['MAIL_PASSWORD'] = 'oddb lsmo nase qwpp'
app.config['MAIL_DEFAULT_SENDER'] = 'shivanilookup@gmail.com'

# ✅ Mail and CSRF setup
mail = Mail(app)
mfa_secret = pyotp.random_base32()
app.config['SECRET_KEY'] = 'yoursupersecrettokenhere'
csrf = CSRFProtect(app) 

@app.route("/", methods=['GET'])
def home():
    if not is_logged_in():
        return render_template("login.html")
    return redirect('/dashboard')


# ✅ JWT token creation with expiration
def create_token(email):
    now = datetime.utcnow()
    payload = {'sub': email, 'iat': now, 'exp': now + timedelta(minutes=60)}
    token = jwt.encode(payload, SECRET, algorithm='HS256')
    return token

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email")
    password = request.form.get("password")

    con = sqlite3.connect("bank.db")
    cur = con.cursor()
    cur.execute("SELECT email, password FROM users WHERE email = ?", (email,))
    row = cur.fetchone()

    if not row:
        con.close()
        return render_template("login.html", error="Invalid credentials")

    stored_email, stored_password = row
     # ✅ Timing-safe password verification
    if not pbkdf2_sha256.verify(password, stored_password):
        con.close()
        return render_template("login.html", error="Invalid credentials")

    # ✅ Generate a 6-digit OTP
    otp = str(random.randint(100000, 999999))

    # ✅ Save OTP in DB
    cur.execute("UPDATE users SET login_otp = ? WHERE email = ?", (otp, email))
    con.commit()
    con.close()

    # ✅ Send OTP via email
    msg = Message("Your Login OTP", recipients=[email])
    msg.body = f"Your One-Time Password (OTP) is: {otp}"
    mail.send(msg)

    session["pending_login_email"] = email
    flash("A 6-digit OTP has been sent to your email.")
    return redirect("/verify-otp")

@app.route("/dashboard", methods=["GET"])
@logged_in
def dashboard():
    token = request.cookies.get("auth_token")
    if not token:
        return redirect("/")

    try:
        data = jwt.decode(token, SECRET, algorithms=['HS256'])
        email = data["sub"]
    except jwt.InvalidTokenError:
        return render_template("400.html"), 400

    con = sqlite3.connect("bank.db")
    cur = con.cursor()

    # Fetch name and username from users table
    cur.execute("SELECT name, username FROM users WHERE email = ?", (email,))
    row = cur.fetchone()
    if not row:
        con.close()
        return render_template("404.html"), 404

    name, username = row

    # Fetch user accounts
    cur.execute("SELECT id, type FROM accounts WHERE owner = ?", (email,))
    accounts = cur.fetchall()
    con.close()

    # Pass full name and username to template
    return render_template("dashboard.html", user=name, username=username, accounts=accounts)

@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    if request.method == "GET":
        return render_template("verify_otp.html")

    otp_input = request.form.get("otp")
    email = session.get("pending_login_email")

    con = sqlite3.connect("bank.db")
    cur = con.cursor()
    cur.execute("SELECT login_otp FROM users WHERE email = ?", (email,))
    row = cur.fetchone()
    con.close()

    if row and row[0] == otp_input:
        session.pop("pending_login_email", None)
        token = create_token(email)
        response = make_response(redirect("/dashboard"))
        response.set_cookie("auth_token", token)
        return response, 303

    return render_template("verify_otp.html", error="Invalid OTP. Try again.")


@app.route("/mfa", methods=["GET", "POST"])
def mfa():
    email = session.get("pending_mfa")
    if not email:
        return redirect("/")

    if request.method == "GET":
        return render_template("mfa.html")  # has 6-digit input field

    # POST: verify code
    code = request.form.get("code")
    con = sqlite3.connect('bank.db')
    cur = con.cursor()
    cur.execute("SELECT mfa_secret FROM users WHERE email = ?", (email,))
    row = cur.fetchone()
    con.close()

    if row:
        mfa_secret = row[0]
        totp = pyotp.TOTP(mfa_secret)
        if totp.verify(code):
            session.pop("pending_mfa")
            response = make_response(redirect("/dashboard"))
            response.set_cookie("auth_token", create_token(email))
            return response, 303

    return render_template("mfa.html", error="Invalid authentication code")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    # Grab data
    first_name = request.form.get("first_name")
    last_name = request.form.get("last_name")
    email = request.form.get("email")
    password = request.form.get("password")
    account_type = request.form.getlist("account_type")

    if len(password) < 8:
        return render_template("register.html", error="Password must be at least 8 characters long")

    username = email.split("@")[0] + "_001"
    hash = pbkdf2_sha256.hash(password)
    mfa_secret = pyotp.random_base32()  # ✅ Generate MFA secret

    try:
        con = sqlite3.connect('bank.db')
        cur = con.cursor()

        # Insert user with MFA secret
        full_name = first_name + " " + last_name
        cur.execute("INSERT INTO users (email, name, password, username, mfa_secret) VALUES (?, ?, ?, ?, ?)", 
                    (email, full_name, hash, username, mfa_secret))

        # Add accounts
        if "savings" in account_type or "both" in account_type:
            cur.execute("INSERT INTO accounts (id, owner, balance, type) VALUES (?, ?, ?, ?)", 
                        (username + "_SAV", email, 300, "savings"))
        if "checking" in account_type or "both" in account_type:
            cur.execute("INSERT INTO accounts (id, owner, balance, type) VALUES (?, ?, ?, ?)", 
                        (username + "_CHK", email, 500, "checking"))

        con.commit()
        con.close()

        flash("✅ Account created! Please log in.")
        return redirect("/")
    except sqlite3.IntegrityError:
        return render_template("register.html", error="Email already registered")
    
@app.route("/details", methods=['GET'])
@logged_in
def details():
    account_number = request.args['account']
    return render_template(
        "details.html", 
        user=g.user,
        account_number=account_number,
        balance=get_balance(account_number, g.user))

@app.route("/logout", methods=['GET'])
def logout():
    response = make_response(redirect("/dashboard"))
    response.delete_cookie('auth_token')
    return response, 303

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

def send_mail(subject, recipient, body):
    msg = Message(subject=subject, recipients=[recipient], body=body)
    mail.send(msg)


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "GET":
        return render_template("forgot_password.html")

    email = request.form.get("email")

    con = sqlite3.connect('bank.db')
    cur = con.cursor()
    cur.execute("SELECT email FROM users WHERE email = ?", (email,))
    row = cur.fetchone()
    con.close()

    if not row:
        flash("If your email exists in our system, a reset link has been sent.")
        return redirect("/")

    token = create_token(email)
    reset_link = f"http://127.0.0.1:5000/reset-password/{token}"
    send_mail(
    subject="Reset Your Password",
    recipient=email,
    body=f"Hi,\n\nClick this link to reset your password:\n{reset_link}\n\nThis link expires in 60 minutes.")

    flash("Reset link sent to your email.")

    return redirect("/")


@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    print("👉 Using DB at:", os.path.abspath("bank.db"))

    try:
        data = jwt.decode(token, SECRET, algorithms=['HS256'])
        email = data["sub"]
    except jwt.InvalidTokenError:
        return render_template("400.html"), 400

    if request.method == "GET":
        return render_template("reset_password.html", token=token)

    password = request.form.get("password")
    if len(password) < 8:
        return render_template("reset_password.html", token=token, error="Password must be at least 8 characters")

    hashed_password = pbkdf2_sha256.hash(password)


    con = sqlite3.connect("bank.db")
    cur = con.cursor()
    cur.execute("UPDATE users SET password = ? WHERE email = ?", (hashed_password, email))

    con.commit()
    con.close()
    

    flash("✅ Password reset successful! You can now log in.")
    return redirect("/")

@app.route("/transfer", methods=["GET", "POST"])
@logged_in
def transfer():
    user_email = g.user
    con = sqlite3.connect("bank.db")
    cur = con.cursor()

    # Get the user's accounts
    cur.execute("SELECT id, type, balance FROM accounts WHERE owner = ?", (user_email,))
    user_accounts = cur.fetchall()

    if request.method == "GET":
        con.close()
        return render_template("transfer.html", accounts=user_accounts)

    from_account = request.form.get("from_account")
    to_account = request.form.get("to_account")
    amount = request.form.get("amount")

    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError("Amount must be positive")
    except ValueError:
        con.close()
        return render_template("transfer.html", accounts=user_accounts, error="Invalid amount")

    # Validate source account
    cur.execute("SELECT balance FROM accounts WHERE id = ? AND owner = ?", (from_account, user_email))
    row = cur.fetchone()
    if not row:
        con.close()
        return render_template("transfer.html", accounts=user_accounts, error="Invalid source account")

    if row[0] < amount:
        con.close()
        return render_template("transfer.html", accounts=user_accounts, error="Insufficient funds")

    # Validate destination
    cur.execute("SELECT id FROM accounts WHERE id = ?", (to_account,))
    if not cur.fetchone():
        con.close()
        return render_template("transfer.html", accounts=user_accounts, error="Destination account not found")

    # Transfer
    cur.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, from_account))
    cur.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, to_account))
    con.commit()
    con.close()

    flash("✅ Transfer complete")
    return redirect("/dashboard")

