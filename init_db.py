import os
import sqlite3
from werkzeug.security import generate_password_hash
from app import app, get_db, init_database, now

with app.app_context():
    init_database()
    email = os.environ.get("ADMIN_EMAIL", "admin@example.com")
    password = os.environ.get("ADMIN_PASSWORD")
    if not password or len(password) < 8:
        raise SystemExit("Set ADMIN_PASSWORD to a password of at least 8 characters before running init_db.py.")
    db = get_db()
    try:
        db.execute("INSERT INTO users (name,email,phone,password_hash,blood_group,dob,gender,address,role,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)", ("System Administrator", email.lower(), "0000000000", generate_password_hash(password), "O+", "2000-01-01", "Other", "Local blood bank office", "admin", now()))
        db.commit()
        print("Admin account created for " + email.lower())
    except sqlite3.IntegrityError:
        print("That admin email already exists; no account was changed.")
