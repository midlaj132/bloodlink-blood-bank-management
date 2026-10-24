# Blood Bank Management System

A college-level blood bank application built with Python, Flask, SQLite, Jinja2, Bootstrap 5, and vanilla JavaScript. It demonstrates authentication, donor records, inventory, blood requests, compatibility guidance, and administrator workflows. It is educational software; real transfusion decisions must be made by qualified medical professionals.

## Features
- Registration, login, logout, hashed passwords, sessions, and role-based admin authorization.
- Donor registration, search, filters, editing, and ownership checks.
- Eight blood groups with non-negative inventory controls.
- Requests with Pending, Approved, Rejected, and Completed statuses.
- Compatible blood group display and automatic inventory deduction on completion.
- Blood bank records and admin dashboard statistics.

## Setup on Windows in VS Code
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
$env:SECRET_KEY = "replace-with-a-long-random-value"
$env:ADMIN_EMAIL = "admin@example.com"
$env:ADMIN_PASSWORD = "Choose-a-password-8-chars-or-more"
python init_db.py
python app.py
```
Open `http://127.0.0.1:5000/` in a browser. On Command Prompt, use `set SECRET_KEY=...`, `set ADMIN_EMAIL=...`, and `set ADMIN_PASSWORD=...` instead of PowerShell syntax.

## Admin setup
Run `init_db.py` once with `ADMIN_EMAIL` and `ADMIN_PASSWORD` set. The password is never written into source code. The script will not overwrite an existing email. Log in using those values to access `/admin` and inventory/request management.

## Deploy on Render
1. Push this project to GitHub and create a new **Blueprint** on Render using that repository. Render detects `render.yaml` and configures the web service.
2. When prompted, set `ADMIN_EMAIL` and `ADMIN_PASSWORD`. Use a unique admin email and a strong password of at least 8 characters; do not commit either value.
3. Deploy the Blueprint. The service uses Gunicorn and a persistent disk mounted at `/var/data` for SQLite, so registered accounts and application records survive restarts and deployments.

The Blueprint uses a paid Starter web service because Render persistent disks are not available on free web services. Do not remove the disk or change `DATABASE_PATH` to the ephemeral application filesystem if you need to keep user data. The default committed `database.db` is not deployed to Render; the persistent database is initialized on the mounted disk.

## Project structure
`app.py` contains routes, validation, authorization, and database access. `init_db.py` creates the first admin. Templates provide the pages, while `static/css/style.css` and `static/js/script.js` provide shared presentation and behavior. `database.db` is created automatically on first run.

## Usage
Register a user, log in, register as a donor, and submit a request. An administrator can add inventory, approve requests, and complete approved requests. Completing a request checks compatible stock and deducts units without allowing a negative balance.

## Common issues
- `python is not recognized`: install Python 3 and enable “Add Python to PATH”, then reopen VS Code.
- `No module named flask`: activate `venv` and rerun `pip install -r requirements.txt`.
- Admin setup exits: set `ADMIN_PASSWORD` and make sure it has at least eight characters.
- Port in use: change the final line in `app.py` to `app.run(debug=True, port=5001)`.
