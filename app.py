import os
import re
import sqlite3
from functools import wraps
from datetime import datetime
from flask import Flask, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "database.db")
BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
COMPATIBILITY = {
    "A+": ["A+", "A-", "O+", "O-"], "A-": ["A-", "O-"],
    "B+": ["B+", "B-", "O+", "O-"], "B-": ["B-", "O-"],
    "AB+": BLOOD_GROUPS, "AB-": ["A-", "B-", "AB-", "O-"],
    "O+": ["O+", "O-"], "O-": ["O-"]
}
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "local-development-change-this")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_database():
    db = get_db()
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
        phone TEXT NOT NULL, password_hash TEXT NOT NULL, blood_group TEXT NOT NULL,
        dob TEXT NOT NULL, gender TEXT NOT NULL, address TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user', created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS donors (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, name TEXT NOT NULL,
        email TEXT NOT NULL, phone TEXT NOT NULL, blood_group TEXT NOT NULL, dob TEXT NOT NULL,
        gender TEXT NOT NULL, address TEXT NOT NULL, last_donation TEXT, eligibility TEXT NOT NULL,
        created_at TEXT NOT NULL, FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS blood_inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT, blood_group TEXT NOT NULL UNIQUE,
        units INTEGER NOT NULL DEFAULT 0 CHECK(units >= 0), updated_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS blood_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, patient_name TEXT NOT NULL,
        patient_age INTEGER NOT NULL, gender TEXT NOT NULL, blood_group TEXT NOT NULL,
        units_required INTEGER NOT NULL CHECK(units_required > 0), hospital_name TEXT NOT NULL,
        hospital_contact TEXT NOT NULL, reason TEXT NOT NULL, urgency TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Pending', created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS blood_banks (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, address TEXT NOT NULL,
        phone TEXT NOT NULL, email TEXT NOT NULL, operating_hours TEXT NOT NULL
    );
    """)
    for group in BLOOD_GROUPS:
        db.execute("INSERT OR IGNORE INTO blood_inventory (blood_group, units, updated_at) VALUES (?, 0, ?)", (group, now()))
    db.commit()


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def valid_email(value):
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value or "") is not None


def valid_phone(value):
    return re.match(r"^[0-9+()\-\s]{7,20}$", value or "") is not None


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        if g.user["role"] != "admin":
            flash("Administrator access is required.", "danger")
            return redirect(url_for("dashboard"))
        return view(*args, **kwargs)
    return wrapped


@app.before_request
def load_user():
    init_database()
    user_id = session.get("user_id")
    g.user = get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone() if user_id else None


@app.context_processor
def template_data():
    return {"blood_groups": BLOOD_GROUPS, "compatibility": COMPATIBILITY}


@app.route("/")
def index():
    db = get_db()
    stats = {
        "donors": db.execute("SELECT COUNT(*) AS value FROM donors").fetchone()["value"],
        "units": db.execute("SELECT COALESCE(SUM(units), 0) AS value FROM blood_inventory").fetchone()["value"],
        "requests": db.execute("SELECT COUNT(*) AS value FROM blood_requests").fetchone()["value"],
        "groups": db.execute("SELECT COUNT(*) AS value FROM blood_inventory WHERE units > 0").fetchone()["value"]
    }
    inventory = db.execute("SELECT * FROM blood_inventory ORDER BY id").fetchall()
    return render_template("index.html", stats=stats, inventory=inventory)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        form = request.form
        required = ["name", "email", "phone", "password", "blood_group", "dob", "gender", "address"]
        if any(not form.get(field, "").strip() for field in required):
            flash("Please complete every required field.", "danger")
        elif not valid_email(form["email"].strip()) or not valid_phone(form["phone"].strip()):
            flash("Enter a valid email address and phone number.", "danger")
        elif len(form["password"]) < 8:
            flash("Password must contain at least 8 characters.", "danger")
        elif form["blood_group"] not in BLOOD_GROUPS:
            flash("Select a valid blood group.", "danger")
        else:
            try:
                db = get_db()
                cursor = db.execute("""INSERT INTO users (name,email,phone,password_hash,blood_group,dob,gender,address,role,created_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?)""", (form["name"].strip(), form["email"].strip().lower(), form["phone"].strip(),
                    generate_password_hash(form["password"]), form["blood_group"], form["dob"], form["gender"], form["address"].strip(), "user", now()))
                db.commit()
                session.clear()
                session["user_id"] = cursor.lastrowid
                flash("Registration successful. Welcome!", "success")
                return redirect(url_for("dashboard"))
            except sqlite3.IntegrityError:
                flash("An account with that email already exists.", "danger")
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = get_db().execute("SELECT * FROM users WHERE email = ?", (request.form.get("email", "").strip().lower(),)).fetchone()
        if user and check_password_hash(user["password_hash"], request.form.get("password", "")):
            session.clear()
            session["user_id"] = user["id"]
            return redirect(request.args.get("next") or url_for("dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    requests = db.execute("SELECT * FROM blood_requests WHERE user_id = ? ORDER BY id DESC LIMIT 5", (g.user["id"],)).fetchall()
    counts = {
        "donors": db.execute("SELECT COUNT(*) AS value FROM donors").fetchone()["value"],
        "units": db.execute("SELECT COALESCE(SUM(units),0) AS value FROM blood_inventory").fetchone()["value"],
        "pending": db.execute("SELECT COUNT(*) AS value FROM blood_requests WHERE status = 'Pending'").fetchone()["value"]
    }
    return render_template("dashboard.html", requests=requests, counts=counts)


@app.route("/donor", methods=["GET", "POST"])
@app.route("/donor/add", methods=["GET", "POST"])
@login_required
def donor_add():
    if request.method == "POST":
        form = request.form
        if not all(form.get(key, "").strip() for key in ["name", "email", "phone", "blood_group", "dob", "gender", "address", "eligibility"]):
            flash("Complete all donor fields.", "danger")
        elif not valid_email(form["email"]) or not valid_phone(form["phone"]):
            flash("Enter a valid donor email and phone number.", "danger")
        else:
            db = get_db()
            db.execute("""INSERT INTO donors (user_id,name,email,phone,blood_group,dob,gender,address,last_donation,eligibility,created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""", (g.user["id"], form["name"].strip(), form["email"].strip(), form["phone"].strip(), form["blood_group"], form["dob"], form["gender"], form["address"].strip(), form.get("last_donation") or None, form["eligibility"], now()))
            db.commit()
            flash("Donor registered successfully.", "success")
            return redirect(url_for("donors"))
    return render_template("donor.html", donor=None)


@app.route("/donor/edit/<int:donor_id>", methods=["GET", "POST"])
@login_required
def donor_edit(donor_id):
    db = get_db()
    donor = db.execute("SELECT * FROM donors WHERE id = ?", (donor_id,)).fetchone()
    if donor is None:
        return render_template("404.html"), 404
    if donor["user_id"] != g.user["id"] and g.user["role"] != "admin":
        flash("You cannot edit another user's donor record.", "danger")
        return redirect(url_for("donors"))
    if request.method == "POST":
        form = request.form
        db.execute("""UPDATE donors SET name=?,email=?,phone=?,blood_group=?,dob=?,gender=?,address=?,last_donation=?,eligibility=? WHERE id=?""", (form["name"], form["email"], form["phone"], form["blood_group"], form["dob"], form["gender"], form["address"], form.get("last_donation") or None, form["eligibility"], donor_id))
        db.commit()
        flash("Donor record updated.", "success")
        return redirect(url_for("donors"))
    return render_template("donor.html", donor=donor)


@app.route("/donor/delete/<int:donor_id>", methods=["POST"])
@login_required
def donor_delete(donor_id):
    db = get_db()
    donor = db.execute("SELECT user_id FROM donors WHERE id = ?", (donor_id,)).fetchone()
    if donor and (donor["user_id"] == g.user["id"] or g.user["role"] == "admin"):
        db.execute("DELETE FROM donors WHERE id = ?", (donor_id,)); db.commit(); flash("Donor deleted.", "success")
    else:
        flash("You are not allowed to delete this record.", "danger")
    return redirect(url_for("donors"))


@app.route("/donors")
@login_required
def donors():
    filters = request.args
    query = "SELECT * FROM donors WHERE 1=1"
    values = []
    if filters.get("q"):
        query += " AND (name LIKE ? OR email LIKE ? OR phone LIKE ?)"; term = "%" + filters["q"] + "%"; values.extend([term, term, term])
    if filters.get("blood_group"):
        query += " AND blood_group = ?"; values.append(filters["blood_group"])
    if filters.get("gender"):
        query += " AND gender = ?"; values.append(filters["gender"])
    donors_list = get_db().execute(query + " ORDER BY id DESC", values).fetchall()
    return render_template("donors.html", donors=donors_list)


@app.route("/inventory")
@login_required
def inventory():
    return render_template("inventory.html", inventory=get_db().execute("SELECT * FROM blood_inventory ORDER BY id").fetchall())


@app.route("/inventory/add", methods=["POST"])
@admin_required
def inventory_add():
    return inventory_update_impl()


@app.route("/inventory/update/<int:item_id>", methods=["POST"])
@admin_required
def inventory_update(item_id):
    return inventory_update_impl(item_id)


def inventory_update_impl(item_id=None):
    group = request.form.get("blood_group")
    try:
        units = int(request.form.get("units", "0"))
        if units < 0 or group not in BLOOD_GROUPS: raise ValueError
    except ValueError:
        flash("Blood group and a non-negative whole number of units are required.", "danger")
        return redirect(url_for("inventory"))
    db = get_db()
    if item_id:
        db.execute("UPDATE blood_inventory SET units=?, updated_at=? WHERE id=?", (units, now(), item_id))
    else:
        db.execute("UPDATE blood_inventory SET units=?, updated_at=? WHERE blood_group=?", (units, now(), group))
    db.commit(); flash("Inventory updated.", "success")
    return redirect(url_for("inventory"))


@app.route("/request", methods=["GET", "POST"])
@login_required
def request_blood():
    if request.method == "POST":
        form = request.form
        try: age, units = int(form["patient_age"]), int(form["units_required"])
        except (KeyError, ValueError): age, units = 0, 0
        fields = ["patient_name", "gender", "blood_group", "hospital_name", "hospital_contact", "reason", "urgency"]
        if not all(form.get(field, "").strip() for field in fields) or age < 1 or units < 1 or form["blood_group"] not in BLOOD_GROUPS:
            flash("Complete the request with valid age, blood group, and units.", "danger")
        elif form["urgency"] not in ["Normal", "Urgent", "Emergency"]:
            flash("Select a valid urgency.", "danger")
        else:
            db = get_db(); db.execute("""INSERT INTO blood_requests (user_id,patient_name,patient_age,gender,blood_group,units_required,hospital_name,hospital_contact,reason,urgency,status,created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", (g.user["id"], form["patient_name"], age, form["gender"], form["blood_group"], units, form["hospital_name"], form["hospital_contact"], form["reason"], form["urgency"], "Pending", now())); db.commit()
            flash("Blood request submitted.", "success"); return redirect(url_for("requests"))
    return render_template("request.html")


@app.route("/requests")
@login_required
def requests():
    db = get_db(); query = "SELECT blood_requests.*, users.name AS requester FROM blood_requests JOIN users ON users.id = blood_requests.user_id WHERE 1=1"; values = []
    if g.user["role"] != "admin": query += " AND user_id = ?"; values.append(g.user["id"])
    for field in ["blood_group", "status", "urgency"]:
        if request.args.get(field): query += " AND blood_requests." + field + " = ?"; values.append(request.args[field])
    if request.args.get("q"): query += " AND (patient_name LIKE ? OR hospital_name LIKE ?)"; term = "%" + request.args["q"] + "%"; values.extend([term, term])
    records = db.execute(query + " ORDER BY blood_requests.id DESC", values).fetchall()
    return render_template("requests.html", requests=records)


@app.route("/request/<int:request_id>")
@login_required
def request_detail(request_id):
    record = get_db().execute("SELECT * FROM blood_requests WHERE id = ?", (request_id,)).fetchone()
    if not record or (record["user_id"] != g.user["id"] and g.user["role"] != "admin"): return render_template("404.html"), 404
    return render_template("request.html", blood_request=record)


def change_request_status(request_id, status):
    db = get_db(); record = db.execute("SELECT * FROM blood_requests WHERE id=?", (request_id,)).fetchone()
    if not record: flash("Request not found.", "danger"); return redirect(url_for("requests"))
    if status == "Completed" and record["status"] != "Completed":
        compatible = COMPATIBILITY[record["blood_group"]]
        inventory_rows = db.execute("SELECT * FROM blood_inventory WHERE units > 0 ORDER BY units DESC").fetchall()
        available = sum(item["units"] for item in inventory_rows if item["blood_group"] in compatible)
        if available < record["units_required"]: flash("Not enough compatible blood units to complete this request.", "danger"); return redirect(url_for("requests"))
        remaining = record["units_required"]
        for item in inventory_rows:
            if item["blood_group"] not in compatible:
                continue
            used = min(remaining, item["units"]); db.execute("UPDATE blood_inventory SET units=units-?, updated_at=? WHERE id=?", (used, now(), item["id"])); remaining -= used
            if remaining == 0: break
    db.execute("UPDATE blood_requests SET status=? WHERE id=?", (status, request_id)); db.commit(); flash("Request status updated.", "success"); return redirect(url_for("requests"))


@app.route("/request/approve/<int:request_id>", methods=["POST"])
@admin_required
def request_approve(request_id): return change_request_status(request_id, "Approved")


@app.route("/request/reject/<int:request_id>", methods=["POST"])
@admin_required
def request_reject(request_id): return change_request_status(request_id, "Rejected")


@app.route("/request/complete/<int:request_id>", methods=["POST"])
@admin_required
def request_complete(request_id): return change_request_status(request_id, "Completed")


@app.route("/blood-banks", methods=["GET", "POST"])
@login_required
def blood_banks():
    if request.method == "POST":
        if g.user["role"] != "admin": flash("Administrator access is required.", "danger")
        elif not all(request.form.get(field, "").strip() for field in ["name", "address", "phone", "email", "operating_hours"]): flash("Complete all blood bank fields.", "danger")
        else:
            db = get_db(); db.execute("INSERT INTO blood_banks (name,address,phone,email,operating_hours) VALUES (?,?,?,?,?)", tuple(request.form[field].strip() for field in ["name", "address", "phone", "email", "operating_hours"])); db.commit(); flash("Blood bank added.", "success")
    return render_template("blood_banks.html", banks=get_db().execute("SELECT * FROM blood_banks ORDER BY name").fetchall())


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        form = request.form
        if not valid_phone(form.get("phone")) or not form.get("name", "").strip(): flash("Enter a valid name and phone number.", "danger")
        else:
            db = get_db(); db.execute("UPDATE users SET name=?,phone=?,blood_group=?,dob=?,gender=?,address=? WHERE id=?", (form["name"].strip(), form["phone"].strip(), form["blood_group"], form["dob"], form["gender"], form["address"].strip(), g.user["id"])); db.commit(); flash("Profile updated.", "success"); return redirect(url_for("profile"))
    return render_template("profile.html")


@app.route("/admin")
@admin_required
def admin():
    db = get_db(); stats = {
        "users": db.execute("SELECT COUNT(*) AS value FROM users").fetchone()["value"],
        "donors": db.execute("SELECT COUNT(*) AS value FROM donors").fetchone()["value"],
        "requests": db.execute("SELECT COUNT(*) AS value FROM blood_requests").fetchone()["value"]
    }
    stats["units"] = db.execute("SELECT COALESCE(SUM(units),0) AS value FROM blood_inventory").fetchone()["value"]
    stats["pending"] = db.execute("SELECT COUNT(*) AS value FROM blood_requests WHERE status='Pending'").fetchone()["value"]
    stats["approved"] = db.execute("SELECT COUNT(*) AS value FROM blood_requests WHERE status='Approved'").fetchone()["value"]
    stats["rejected"] = db.execute("SELECT COUNT(*) AS value FROM blood_requests WHERE status='Rejected'").fetchone()["value"]
    return render_template("dashboard.html", admin_stats=stats, requests=db.execute("SELECT * FROM blood_requests ORDER BY id DESC LIMIT 8").fetchall(), counts=stats)


@app.route("/admin/users")
@admin_required
def admin_users():
    return render_template("profile.html", users=get_db().execute("SELECT id,name,email,phone,role,created_at FROM users ORDER BY id DESC").fetchall(), admin_view=True)


@app.errorhandler(404)
def not_found(error): return render_template("404.html"), 404


with app.app_context(): init_database()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1")
