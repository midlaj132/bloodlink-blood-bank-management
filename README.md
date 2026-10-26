# Blood Bank Management System

A college-level blood bank application built with Python, Flask, SQLite for local development, PostgreSQL for hosted deployments, Jinja2, Bootstrap 5, and vanilla JavaScript. It demonstrates authentication, donor records, inventory, blood requests, compatibility guidance, and administrator workflows. It is educational software; real transfusion decisions must be made by qualified medical professionals.

## Features
- Registration, login, logout, hashed passwords, sessions, and role-based admin authorization.
- Donor registration, search, filters, editing, and ownership checks.
- Donation eligibility checks for minimum age 18, at least 6 hours' sleep, a 6-month interval after the previous donation, and administrator-verified negative HIV screening. Donors can optionally self-report an HIV status, but it is not treated as a verified test result.
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
1. Create a new **Blueprint** on Render using this GitHub repository. Render detects `render.yaml` and configures the free web service.
2. When prompted, set `ADMIN_EMAIL` and `ADMIN_PASSWORD`. Use a unique admin email and a strong password of at least 8 characters; do not commit either value.
3. Deploy the Blueprint. The app initializes its SQLite database at startup and serves it with Gunicorn.

The free service uses ephemeral storage and may spin down when idle. SQLite accounts, donor records, requests, and inventory can be lost on restart, redeploy, or instance replacement. This setup is suitable for a demo only; use a paid service with persistent storage or a managed database for data that must be retained.

## Deploy on Vercel
Vercel runs Flask as a serverless function. Configure PostgreSQL for persistent user, donor, request, and inventory data; the local SQLite database is only used when `DATABASE_URL` is not set outside Vercel.

1. Create a PostgreSQL database with a hosted provider and copy its connection URL. Keep the URL private.
2. Set `DATABASE_URL` in the Vercel project environment variables, along with a random `SECRET_KEY`, `ADMIN_EMAIL`, and `ADMIN_PASSWORD`.
3. Before deploying, initialize the tables and admin account against that same database from a trusted local machine. In PowerShell:
   ```powershell
   $env:DATABASE_URL = "your-private-postgresql-connection-url"
   $env:ADMIN_EMAIL = "admin@example.com"
   $env:ADMIN_PASSWORD = "a-strong-password"
   python init_db.py
   ```
   Do not commit the connection URL or password. `init_db.py` creates the tables and adds the admin account if that email does not already exist.
4. Push the repository to GitHub, import it into Vercel, and deploy. `vercel.json` routes requests through `api/index.py`.

Vercel requires both `DATABASE_URL` and `SECRET_KEY`; it will fail clearly rather than silently using temporary SQLite storage if either is missing. Existing records in `database.db` are not automatically copied to PostgreSQL.

## Project structure
`app.py` contains routes, validation, authorization, and database access. `init_db.py` creates the first admin. Templates provide the pages, while `static/css/style.css` and `static/js/script.js` provide shared presentation and behavior. `database.db` is created automatically on first run.

## Usage
Register a user, log in, register as a donor, and submit a request. An administrator can add inventory, approve requests, and complete approved requests. Completing a request checks compatible stock and deducts units without allowing a negative balance.

Donated units are added to inventory only when all configured donor eligibility checks pass. Donors can optionally self-report Negative, Positive, or Unsure, but self-reported status does not affect eligibility. Only an administrator can record the verified HIV screening result, and donations remain blocked until a negative result is verified. HIV status is not shown in the donor list. These are educational workflow checks, not medical advice or a substitute for screening and eligibility decisions by qualified blood-bank staff.

## Common issues
- `python is not recognized`: install Python 3 and enable “Add Python to PATH”, then reopen VS Code.
- `No module named flask`: activate `venv` and rerun `pip install -r requirements.txt`.
- Admin setup exits: set `ADMIN_PASSWORD` and make sure it has at least eight characters.
- Port in use: change the final line in `app.py` to `app.run(debug=True, port=5001)`.
