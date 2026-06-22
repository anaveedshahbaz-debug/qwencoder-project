"""
NESPAK Project Monitoring System — Web Application
Run: python app.py
Open: http://localhost:5000
"""
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
import sqlite3, os, json, shutil
from datetime import date, datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = "nespak_pms_secret_2025"

# ── CONFIG ────────────────────────────────────────────────────────────────────
DB_FILE       = "nespak_pms.db"
UPLOAD_FOLDER = "static/uploads"
EXPORT_FOLDER = "exports"
ADMIN_PASSWORD = "admin123"
GUEST_PASSWORD = "guest123"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(EXPORT_FOLDER, exist_ok=True)

TAX_RATES = {
    "PST Punjab 16%": 16.0,
    "PST Sindh 15%": 15.0,
    "PST KPK 15%": 15.0,
    "PST Balochistan 15%": 15.0,
    "GST Federal 18%": 18.0,
    "Exempt 0%": 0.0,
}

PROJECT_MANAGERS = [
    "Zahid Mehmood Khan","Imran Badar","Waseem Saif Dar",
    "Muhammad Aslam Soomro","Ahmad Naveed Shahbaz","Arslan Zamir",
    "Aftab Ahmed","Jamshaid Faisal Janjua","Sanaullah Hashmi","Sajid Hamid",
]
PROJECT_GROUPS = ["RRUDP","CBD","LDA","GPI","PMA","TMT","TEPA","SA","GENERAL","ADP","OTHER"]
INVOICE_PREFIX = "013"

# ── DATABASE ──────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def query(sql, params=(), one=False):
    with get_db() as c:
        cur = c.execute(sql, params)
        return cur.fetchone() if one else cur.fetchall()

def execute(sql, params=()):
    with get_db() as c:
        cur = c.execute(sql, params)
        c.commit()
        return cur.lastrowid

def init_db():
    with get_db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sheet_ref TEXT, job_no TEXT, project_name TEXT NOT NULL,
            client_name TEXT, project_manager TEXT NOT NULL,
            project_group TEXT DEFAULT 'GENERAL',
            comm_date TEXT, comp_date TEXT,
            amendment TEXT DEFAULT 'None', duration_months REAL DEFAULT 0,
            nespak_fee_mil REAL DEFAULT 0,
            salary_cost_est REAL DEFAULT 0, direct_cost_est REAL DEFAULT 0,
            is_active INTEGER DEFAULT 1, remarks TEXT,
            created_at TEXT DEFAULT (date('now')),
            updated_at TEXT DEFAULT (date('now'))
        );
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            contact TEXT, email TEXT, address TEXT,
            created_at TEXT DEFAULT (date('now'))
        );
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            txn_month INTEGER NOT NULL, txn_year INTEGER NOT NULL,
            txn_type TEXT NOT NULL,
            amount REAL DEFAULT 0,
            invoice_no TEXT, invoice_date TEXT,
            tax_type TEXT, tax_rate REAL DEFAULT 0,
            tax_amount REAL DEFAULT 0, gross_amount REAL DEFAULT 0,
            cheque_no TEXT, cheque_date TEXT, cheque_amount REAL DEFAULT 0,
            it_adjustable REAL DEFAULT 0, pra_adjustable REAL DEFAULT 0,
            other_adjustable REAL DEFAULT 0,
            st_received REAL DEFAULT 0, other_non_adj REAL DEFAULT 0,
            amount_received REAL DEFAULT 0,
            salary_actual REAL DEFAULT 0, direct_actual REAL DEFAULT 0,
            description TEXT, attachment_path TEXT,
            entry_date TEXT DEFAULT (date('now')),
            updated_at TEXT DEFAULT (date('now'))
        );
        CREATE TABLE IF NOT EXISTS monthly_snapshot (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            snap_month INTEGER NOT NULL, snap_year INTEGER NOT NULL,
            billing_upto REAL DEFAULT 0, receipt_upto REAL DEFAULT 0,
            salary_upto REAL DEFAULT 0, direct_upto REAL DEFAULT 0,
            receivable REAL DEFAULT 0,
            profit_loss_billing REAL DEFAULT 0,
            profit_loss_receipt REAL DEFAULT 0,
            UNIQUE(project_id, snap_month, snap_year)
        );
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);

        CREATE TABLE IF NOT EXISTS project_clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            client_name TEXT NOT NULL,
            client_ntn TEXT,
            created_at TEXT DEFAULT (date('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_projclients_proj ON project_clients(project_id);

        CREATE TABLE IF NOT EXISTS edit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name TEXT, record_id INTEGER,
            field_changed TEXT, old_value TEXT, new_value TEXT,
            changed_by TEXT, changed_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS clients_master (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL UNIQUE,
            short_name TEXT,
            ntn_no TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (date('now')),
            updated_at TEXT DEFAULT (date('now'))
        );

        CREATE TABLE IF NOT EXISTS pm_master (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL UNIQUE,
            employee_code TEXT,
            designation TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (date('now')),
            updated_at TEXT DEFAULT (date('now'))
        );

        CREATE TABLE IF NOT EXISTS tax_rates_master (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tax_name TEXT NOT NULL UNIQUE,
            rate_percent REAL NOT NULL DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (date('now')),
            updated_at TEXT DEFAULT (date('now'))
        );

        CREATE TABLE IF NOT EXISTS banks_master (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bank_name TEXT NOT NULL UNIQUE,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (date('now')),
            updated_at TEXT DEFAULT (date('now'))
        );

        CREATE TABLE IF NOT EXISTS cheques (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cheque_no TEXT NOT NULL,
            cheque_date TEXT,
            amount REAL DEFAULT 0,
            client_name TEXT,
            bank_name TEXT,
            memo_no TEXT,
            remarks TEXT,
            txn_month INTEGER, txn_year INTEGER,
            status TEXT DEFAULT 'Open',
            attachment_path TEXT,
            created_at TEXT DEFAULT (date('now'))
        );

        CREATE TABLE IF NOT EXISTS performas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            performa_no TEXT,
            cheque_id INTEGER REFERENCES cheques(id),
            txn_month INTEGER, txn_year INTEGER,
            total_amount REAL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS performa_lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            performa_id INTEGER NOT NULL REFERENCES performas(id) ON DELETE CASCADE,
            project_id INTEGER NOT NULL REFERENCES projects(id),
            invoice_txn_id INTEGER REFERENCES transactions(id),
            invoice_no TEXT, invoice_date TEXT,
            invoice_amount REAL DEFAULT 0,
            invoice_tax REAL DEFAULT 0,
            invoice_gross REAL DEFAULT 0,
            pst_rate REAL DEFAULT 0, pst_amount REAL DEFAULT 0,
            it_amount REAL DEFAULT 0,
            other_amount REAL DEFAULT 0,
            cheque_share REAL DEFAULT 0,
            st_received REAL DEFAULT 0,
            st_deducted REAL DEFAULT 0,
            extra_st_deducted REAL DEFAULT 0,
            client_name TEXT, client_ntn TEXT,
            remarks TEXT,
            receipt_txn_id INTEGER REFERENCES transactions(id)
        );

        CREATE INDEX IF NOT EXISTS idx_txn_proj ON transactions(project_id);
        CREATE INDEX IF NOT EXISTS idx_txn_period ON transactions(txn_year, txn_month);
        CREATE INDEX IF NOT EXISTS idx_snap_proj ON monthly_snapshot(project_id);
        CREATE INDEX IF NOT EXISTS idx_perfline_perf ON performa_lines(performa_id);
        CREATE INDEX IF NOT EXISTS idx_perfline_proj ON performa_lines(project_id);
        """)
        # migrations
        for col, defn in [
            ("client_name","TEXT"), ("it_adjustable","REAL DEFAULT 0"),
            ("pra_adjustable","REAL DEFAULT 0"),("other_adjustable","REAL DEFAULT 0"),
            ("st_received","REAL DEFAULT 0"),("other_non_adj","REAL DEFAULT 0"),
            ("amount_received","REAL DEFAULT 0"),
            ("st_deducted","REAL DEFAULT 0"),("extra_st_deducted","REAL DEFAULT 0"),
            ("attachment_name","TEXT"),("attachment_skipped","INTEGER DEFAULT 0"),
            ("performa_line_id","INTEGER"),
            ("edit_remarks","TEXT"), ("client_id","INTEGER"),
        ]:
            try: c.execute(f"ALTER TABLE transactions ADD COLUMN {col} {defn}")
            except: pass
        for col, defn in [
            ("client_name","TEXT"), ("client_ntn","TEXT"),
            ("has_multiple_clients","INTEGER DEFAULT 0"),
        ]:
            try: c.execute(f"ALTER TABLE projects ADD COLUMN {col} {defn}")
            except: pass
        for col, defn in [
            ("client_name","TEXT"), ("bank_name","TEXT"), ("memo_no","TEXT"),
            ("attachment_path","TEXT"), ("memo_date","TEXT"), ("fy","TEXT"),
        ]:
            try: c.execute(f"ALTER TABLE cheques ADD COLUMN {col} {defn}")
            except: pass
        for col, defn in [
            ("advance","REAL DEFAULT 0"), ("retention","REAL DEFAULT 0"),
            ("pra_fee","REAL DEFAULT 0"), ("sales_deducted","REAL DEFAULT 0"),
            ("it_deducted","REAL DEFAULT 0"), ("other_ded","REAL DEFAULT 0"),
            ("sales_received","REAL DEFAULT 0"), ("sales_tax_submitted","REAL DEFAULT 0"),
            ("amount_received","REAL DEFAULT 0"), ("cheque_attachment","TEXT"),
            # Table 2 formula fields
            ("t2_invoice_amt","REAL DEFAULT 0"),
            ("t2_it_formula","TEXT"), ("t2_pra_formula","TEXT"), ("t2_oadj_formula","TEXT"),
            ("t2_sded_formula","TEXT"), ("t2_srcv_formula","TEXT"), ("t2_estd_formula","TEXT"), ("t2_oded_formula","TEXT"),
            ("t2_remarks","TEXT"),
        ]:
            try: c.execute(f"ALTER TABLE performa_lines ADD COLUMN {col} {defn}")
            except: pass
        c.commit()

        # Seed pm_master from hardcoded defaults if empty (so dropdowns are never blank)
        pm_count = c.execute("SELECT COUNT(*) FROM pm_master").fetchone()[0]
        if pm_count == 0:
            for name in PROJECT_MANAGERS:
                try: c.execute("INSERT INTO pm_master (full_name) VALUES (?)", (name,))
                except: pass
            # also pick up any PM names already used on projects but missing from the default list
            existing_proj_pms = c.execute("SELECT DISTINCT project_manager FROM projects WHERE project_manager IS NOT NULL").fetchall()
            for row in existing_proj_pms:
                try: c.execute("INSERT INTO pm_master (full_name) VALUES (?)", (row[0],))
                except: pass
            c.commit()

        # Seed clients_master from any client_name already on projects
        client_count = c.execute("SELECT COUNT(*) FROM clients_master").fetchone()[0]
        if client_count == 0:
            existing_clients = c.execute("SELECT DISTINCT client_name FROM projects WHERE client_name IS NOT NULL AND client_name != ''").fetchall()
            for row in existing_clients:
                try: c.execute("INSERT INTO clients_master (full_name) VALUES (?)", (row[0],))
                except: pass
            c.commit()

def rebuild_snapshot(pid, month, year):
    rows = query(
        "SELECT * FROM transactions WHERE project_id=? AND (txn_year<? OR (txn_year=? AND txn_month<=?))",
        (pid, year, year, month))
    billing = sum(float(r["amount"] or 0) for r in rows if r["txn_type"]=="BILLING")
    receipt = sum(float(r["amount_received"] or 0) for r in rows if r["txn_type"]=="RECEIPT")
    salary  = sum(float(r["salary_actual"] or 0) for r in rows if r["txn_type"]=="EXPENSE")
    direct  = sum(float(r["direct_actual"]  or 0) for r in rows if r["txn_type"]=="EXPENSE")
    execute("""
        INSERT INTO monthly_snapshot
            (project_id,snap_month,snap_year,billing_upto,receipt_upto,
             salary_upto,direct_upto,receivable,profit_loss_billing,profit_loss_receipt)
        VALUES (?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(project_id,snap_month,snap_year) DO UPDATE SET
            billing_upto=excluded.billing_upto, receipt_upto=excluded.receipt_upto,
            salary_upto=excluded.salary_upto, direct_upto=excluded.direct_upto,
            receivable=excluded.receivable,
            profit_loss_billing=excluded.profit_loss_billing,
            profit_loss_receipt=excluded.profit_loss_receipt
    """, (pid,month,year,billing,receipt,salary,direct,
          billing-receipt, billing-(salary+direct), receipt-(salary+direct)))

def get_next_invoice_no(pid):
    rows = query(
        "SELECT invoice_no FROM transactions WHERE project_id=? AND txn_type='BILLING' AND invoice_no IS NOT NULL",
        (pid,))
    max_seq = 0
    for r in rows:
        inv = r["invoice_no"]
        if inv and "/" in inv:
            try:
                seq = int(inv.rsplit("/", 1)[-1])
                if seq > max_seq: max_seq = seq
            except ValueError:
                pass
    return max_seq + 1

def get_fy(month, year):
    if month >= 7: return f"{year}-{str(year+1)[-2:]}"
    return f"{year-1}-{str(year)[-2:]}"

def get_current_fy():
    today = date.today()
    if today.month >= 7: return today.year, today.year+1
    return today.year-1, today.year

def fy_months(fy_start):
    months = [(m, fy_start) for m in range(7,13)]
    months += [(m, fy_start+1) for m in range(1,7)]
    return months

MONTHS_FULL_G = ["January","February","March","April","May","June",
                  "July","August","September","October","November","December"]

def resolve_period(fy_start, month, year, cumulative, alias=""):
    """
    Universal filter resolver used by Dashboard, Projects, Reports, and all
    list views (Invoices/Receipts/Expenses/Cheques/Performa).

    Params (all strings from query args, may be empty):
      fy_start   : "" = All-time, or an int-like FY start year (e.g. "2025" -> FY2025-26)
      month/year : optional specific month+year (independent of fy_start)
      cumulative : "1"/"true" = cumulative range, "0"/"false" = single month/FY only
      alias      : optional table alias prefix for txn_month/txn_year columns,
                   e.g. alias="t." produces "t.txn_month" instead of "txn_month"

    Returns dict:
      mode        : 'all' | 'fy' | 'fy_month' | 'month'
      sql_cond    : SQL boolean fragment (no leading AND)
      sql_params  : params list for sql_cond
      label       : human label for UI
      fy_start    : resolved fy_start int or None
      upto_month/upto_year : the right-edge month/year of the range (for snapshot lookups), or None
    """
    yr_col = f"{alias}txn_year"
    mo_col = f"{alias}txn_month"
    cum = str(cumulative).lower() in ("1","true","yes","on") if cumulative != "" else True
    fy_start_i = int(fy_start) if fy_start not in (None, "", "all") else None
    month_i = int(month) if month not in (None, "") else None
    year_i  = int(year)  if year  not in (None, "") else None

    # Case 1: specific Month+Year given (independent of FY per spec)
    if month_i and year_i:
        if cum:
            # cumulative: from start of THAT month's FY (Jul) through the selected month
            fy1 = year_i if month_i >= 7 else year_i - 1
            fy2 = fy1 + 1
            cond = f"(({yr_col} > ? OR ({yr_col}=? AND {mo_col}>=7)) AND ({yr_col} < ? OR ({yr_col}=? AND {mo_col}<=?)))"
            params = [fy1, fy1, year_i, year_i, month_i]
            return {"mode":"fy_month","sql_cond":cond,"sql_params":params,
                    "label": f"{MONTHS_FULL_G[month_i-1]} {year_i} (Cumulative {fy1}-{str(fy2)[-2:]})",
                    "fy_start": fy1, "upto_month": month_i, "upto_year": year_i}
        else:
            cond = f"({mo_col}=? AND {yr_col}=?)"
            params = [month_i, year_i]
            return {"mode":"month","sql_cond":cond,"sql_params":params,
                    "label": f"{MONTHS_FULL_G[month_i-1]} {year_i} only",
                    "fy_start": None, "upto_month": month_i, "upto_year": year_i}

    # Case 2: FY selected, no specific month -> full FY range either way
    if fy_start_i is not None:
        fy2 = fy_start_i + 1
        cond = f"(({yr_col}=? AND {mo_col}>=7) OR ({yr_col}=? AND {mo_col}<=6))"
        params = [fy_start_i, fy2]
        return {"mode":"fy","sql_cond":cond,"sql_params":params,
                "label": f"FY {fy_start_i}-{str(fy2)[-2:]}",
                "fy_start": fy_start_i, "upto_month": 6, "upto_year": fy2}

    # Case 3: "All" - everything since the start
    return {"mode":"all","sql_cond":"1=1","sql_params":[],
            "label":"All Time (Since Start)","fy_start": None,
            "upto_month": None, "upto_year": None}

def get_available_fys():
    """Returns list of {label,value} FY options found in transaction data, newest first, plus current+1 for future entry."""
    rng = query("SELECT MIN(txn_year) miny, MAX(txn_year) maxy FROM transactions", one=True)
    cur1, cur2 = get_current_fy()
    min_y = rng["miny"] if rng and rng["miny"] else cur1
    max_y = rng["maxy"] if rng and rng["maxy"] else cur1
    out = []
    for y in range(max_y+1, min_y-2, -1):
        out.append({"label": f"{y}-{str(y+1)[-2:]}", "value": y})
    return out

# ── AUTH ──────────────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "role" not in session:
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated

# ── PAGES ─────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    if "role" not in session:
        return redirect(url_for("login_page"))
    return redirect(url_for("dashboard"))

@app.route("/login", methods=["GET","POST"])
def login_page():
    if request.method == "POST":
        data = request.get_json()
        role = data.get("role")
        pwd  = data.get("password")
        admin_pwd = query("SELECT value FROM settings WHERE key='ADMIN_PASSWORD'", one=True)
        guest_pwd = query("SELECT value FROM settings WHERE key='GUEST_PASSWORD'", one=True)
        ap = admin_pwd["value"] if admin_pwd and admin_pwd["value"] else ADMIN_PASSWORD
        gp = guest_pwd["value"] if guest_pwd and guest_pwd["value"] else GUEST_PASSWORD
        if role=="admin" and pwd==ap:
            session["role"] = "admin"
            return jsonify({"ok": True, "redirect": "/dashboard"})
        elif role=="guest" and pwd==gp:
            session["role"] = "guest"
            return jsonify({"ok": True, "redirect": "/dashboard"})
        return jsonify({"ok": False, "error": "Incorrect password"})
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", role=session["role"], active="dashboard")

@app.route("/projects")
@login_required
def projects_page():
    return render_template("projects.html", role=session["role"], active="projects")

@app.route("/entry")
@login_required
def entry_page():
    return render_template("entry.html", role=session["role"], active="entry",
                           tax_rates=TAX_RATES)

@app.route("/list/<entity>")
@login_required
def list_page(entity):
    titles = {
        "invoices": ("Invoices", "💰"), "receipts": ("Receipts", "🏦"),
        "expenses": ("Expenses", "📉"), "cheques": ("Cheques", "📑"),
        "performa": ("Sales Tax Performa", "🧾"),
    }
    if entity not in titles:
        return redirect(url_for("dashboard"))
    title, icon = titles[entity]
    # Map entity to entry tab for the "Add Entry" button
    entry_tab_map = {
        "invoices": "billing",
        "receipts": "receipt",
        "expenses": "expense",
        "cheques": "cheques",
        "performa": "performa"
    }
    entry_tab = entry_tab_map.get(entity, "")
    return render_template("list_view.html", role=session["role"],
                           entity=entity, entity_title=title, entity_icon=icon,
                           active=f"list_{entity}", entry_tab=entry_tab)

@app.route("/projects/<int:pid>/view")
@login_required
def project_full_page(pid):
    p = query("SELECT * FROM projects WHERE id=?", (pid,), one=True)
    if not p:
        return "Project not found", 404
    return render_template("project_detail_page.html", role=session["role"], project_id=pid)

@app.route("/reports")
@login_required
def reports_page():
    return render_template("reports.html", role=session["role"], active="reports")

@app.route("/settings")
@login_required
def settings_page():
    return render_template("settings.html", role=session["role"], active="settings")

# ── API: DASHBOARD ────────────────────────────────────────────────────────────
@app.route("/api/dashboard")
@login_required
def api_dashboard():
    today = date.today()
    fy_start_arg = request.args.get("fy_start", "")
    month_arg    = request.args.get("month", "")
    year_arg     = request.args.get("year", "")
    cumulative   = request.args.get("cumulative", "1")
    pm  = request.args.get("pm", "")
    grp = request.args.get("group", "")

    period = resolve_period(fy_start_arg, month_arg, year_arg, cumulative)

    proj_filter_sql = ""
    proj_filter_params = []
    if pm or grp:
        proj_filter_sql = " AND t.project_id IN (SELECT id FROM projects WHERE 1=1"
        if pm:  proj_filter_sql += " AND project_manager=?"; proj_filter_params.append(pm)
        if grp: proj_filter_sql += " AND project_group=?";   proj_filter_params.append(grp)
        proj_filter_sql += ")"

    # ── Determine which months to plot on the chart / table ──────────────────
    # 'all'      -> one bar per FY found in the data (yearly totals)
    # 'fy'       -> 12 months of that FY
    # 'fy_month' -> months from FY-start through the selected month
    # 'month'    -> just that single month
    mnames = ["Jul","Aug","Sep","Oct","Nov","Dec","Jan","Feb","Mar","Apr","May","Jun"]
    chart_data = []
    fy_table = []

    if period["mode"] == "all":
        # one entry per FY present in the data
        fys = get_available_fys()
        fys_sorted = sorted(fys, key=lambda x: x["value"])
        cum_b=cum_r=cum_e=0.0
        for fy in fys_sorted:
            fy1 = fy["value"]; fy2 = fy1+1
            sql = f"SELECT txn_type,SUM(amount) sa,SUM(amount_received) sr,SUM(salary_actual) ss,SUM(direct_actual) sd FROM transactions t WHERE ((txn_year=? AND txn_month>=7) OR (txn_year=? AND txn_month<=6)){proj_filter_sql} GROUP BY txn_type"
            rows = query(sql, [fy1, fy2] + proj_filter_params)
            b=r2=e=0.0
            for r in rows:
                if r["txn_type"]=="BILLING": b=float(r["sa"] or 0)
                if r["txn_type"]=="RECEIPT": r2=float(r["sr"] or 0)
                if r["txn_type"]=="EXPENSE": e=float((r["ss"] or 0)+(r["sd"] or 0))
            if b==0 and r2==0 and e==0: continue
            cum_b+=b; cum_r+=r2; cum_e+=e
            chart_data.append({"month": fy["label"], "month_num": None, "year": None,
                               "billing": round(b/1e6,2), "receipt": round(r2/1e6,2), "expense": round(e/1e6,2)})
            fy_table.append({"month": fy["label"], "month_num": None, "year": None,
                             "billing": round(b/1e6,2), "receipt": round(r2/1e6,2), "expense": round(e/1e6,2),
                             "cum_b": round(cum_b/1e6,2), "cum_r": round(cum_r/1e6,2), "cum_e": round(cum_e/1e6,2)})
    else:
        # build the month list to iterate
        if period["mode"] == "month":
            months_list = [(period["upto_month"], period["upto_year"])]
        elif period["mode"] == "fy_month":
            months_list = [(m,y) for (m,y) in fy_months(period["fy_start"])
                            if (y < period["upto_year"]) or (y == period["upto_year"] and m <= period["upto_month"])]
        else:  # 'fy'
            months_list = fy_months(period["fy_start"])

        cum_b=cum_r=cum_e=0.0
        for (m, y) in months_list:
            sql = f"SELECT txn_type,SUM(amount) sa,SUM(amount_received) sr,SUM(salary_actual) ss,SUM(direct_actual) sd FROM transactions t WHERE txn_month=? AND txn_year=?{proj_filter_sql} GROUP BY txn_type"
            rows = query(sql, [m,y] + proj_filter_params)
            b=r2=e=0.0
            for r in rows:
                if r["txn_type"]=="BILLING": b=float(r["sa"] or 0)
                if r["txn_type"]=="RECEIPT": r2=float(r["sr"] or 0)
                if r["txn_type"]=="EXPENSE": e=float((r["ss"] or 0)+(r["sd"] or 0))
            cum_b+=b; cum_r+=r2; cum_e+=e
            label = f"{mnames[(m-7)%12]}-{str(y)[-2:]}"
            chart_data.append({"month": label, "month_num": m, "year": y,
                               "billing": round(b/1e6,2), "receipt": round(r2/1e6,2), "expense": round(e/1e6,2)})
            fy_table.append({"month": label, "month_num": m, "year": y,
                             "billing": round(b/1e6,2), "receipt": round(r2/1e6,2), "expense": round(e/1e6,2),
                             "cum_b": round(cum_b/1e6,2), "cum_r": round(cum_r/1e6,2), "cum_e": round(cum_e/1e6,2)})

    # ── KPIs for the resolved period ──────────────────────────────────────────
    proj_count_sql = "SELECT COUNT(*) c FROM projects WHERE 1=1"
    proj_count_params = []
    if pm:  proj_count_sql += " AND project_manager=?"; proj_count_params.append(pm)
    if grp: proj_count_sql += " AND project_group=?";   proj_count_params.append(grp)
    total_proj = query(proj_count_sql, proj_count_params, one=True)["c"]
    active_proj= query(proj_count_sql + " AND is_active=1", proj_count_params, one=True)["c"]

    period_sql = f"""SELECT txn_type, SUM(amount) sa, SUM(amount_received) sr,
               SUM(salary_actual) ss, SUM(direct_actual) sd
        FROM transactions t WHERE {period['sql_cond']}{proj_filter_sql} GROUP BY txn_type"""
    period_totals = query(period_sql, period["sql_params"] + proj_filter_params)
    period_billing=period_receipt=period_expense=0.0
    for r in period_totals:
        if r["txn_type"]=="BILLING": period_billing=float(r["sa"] or 0)
        if r["txn_type"]=="RECEIPT": period_receipt=float(r["sr"] or 0)
        if r["txn_type"]=="EXPENSE": period_expense=float((r["ss"] or 0)+(r["sd"] or 0))

    # Receivable: lifetime billing - lifetime receipt, as of the period's upto-date (or latest if 'all')
    if period["upto_month"] and period["upto_year"]:
        recv_cond = "(t.txn_year < ? OR (t.txn_year=? AND t.txn_month<=?))"
        recv_params = [period["upto_year"], period["upto_year"], period["upto_month"]]
    else:
        recv_cond = "1=1"
        recv_params = []
    recv_sql = f"""SELECT
            SUM(CASE WHEN t.txn_type='BILLING' THEN t.amount ELSE 0 END) b,
            SUM(CASE WHEN t.txn_type='RECEIPT' THEN t.amount_received ELSE 0 END) r
        FROM transactions t WHERE {recv_cond}{proj_filter_sql}"""
    recv_row = query(recv_sql, recv_params + proj_filter_params, one=True)
    total_recv = (float(recv_row["b"] or 0) - float(recv_row["r"] or 0)) if recv_row else 0

    # "This month" KPI = always today's actual month regardless of filter (quick-glance figure)
    tm_sql = f"SELECT txn_type, SUM(amount) sa, SUM(amount_received) sr FROM transactions t WHERE txn_month=? AND txn_year=?{proj_filter_sql} GROUP BY txn_type"
    this_m = query(tm_sql, [today.month, today.year] + proj_filter_params)
    tm_billing=tm_receipt=0.0
    for r in this_m:
        if r["txn_type"]=="BILLING": tm_billing=float(r["sa"] or 0)
        if r["txn_type"]=="RECEIPT": tm_receipt=float(r["sr"] or 0)

    return jsonify({
        "kpis": {
            "total_projects": total_proj,
            "active_projects": active_proj,
            "fy_billing":  round(period_billing/1e6,2),
            "fy_receipt":  round(period_receipt/1e6,2),
            "fy_expense":  round(period_expense/1e6,2),
            "total_recv":  round(total_recv/1e6,2),
            "tm_billing":  round(tm_billing/1e6,2),
            "tm_receipt":  round(tm_receipt/1e6,2),
            "fy_label":    period["label"],
        },
        "chart": chart_data,
        "fy_table": fy_table,
        "available_fys": get_available_fys(),
        "current_fy_start": get_current_fy()[0],
        "period_mode": period["mode"],
    })

@app.route("/api/dashboard/month_detail")
@login_required
def api_month_detail():
    """Detailed breakdown for a single month - all projects with billing/receipt/expense in separate columns"""
    month = int(request.args.get("month"))
    year  = int(request.args.get("year"))
    pm    = request.args.get("pm","")
    client= request.args.get("client","")
    job   = request.args.get("job","")

    sql = """
        SELECT p.id project_id, p.sheet_ref, p.job_no, p.project_name,
               p.project_manager, p.client_name, p.project_group,
               SUM(CASE WHEN t.txn_type='BILLING' THEN t.amount ELSE 0 END) billing,
               SUM(CASE WHEN t.txn_type='BILLING' THEN t.tax_amount ELSE 0 END) billing_tax,
               SUM(CASE WHEN t.txn_type='BILLING' THEN t.gross_amount ELSE 0 END) billing_gross,
               COUNT(DISTINCT CASE WHEN t.txn_type='BILLING' THEN t.id END) billing_cnt,
               SUM(CASE WHEN t.txn_type='RECEIPT' THEN t.amount_received ELSE 0 END) receipt,
               COUNT(DISTINCT CASE WHEN t.txn_type='RECEIPT' THEN t.id END) receipt_cnt,
               SUM(CASE WHEN t.txn_type='EXPENSE' THEN t.salary_actual ELSE 0 END) salary,
               SUM(CASE WHEN t.txn_type='EXPENSE' THEN t.direct_actual ELSE 0 END) direct
        FROM projects p
        JOIN transactions t ON t.project_id = p.id
        WHERE t.txn_month=? AND t.txn_year=?
    """
    params = [month, year]
    if pm:     sql += " AND p.project_manager=?"; params.append(pm)
    if client: sql += " AND p.client_name=?";     params.append(client)
    if job:    sql += " AND p.job_no LIKE ?";      params.append(f"%{job}%")
    sql += " GROUP BY p.id HAVING billing>0 OR receipt>0 OR salary>0 OR direct>0 ORDER BY p.project_manager, p.sheet_ref"

    rows = query(sql, params)
    result = [dict(r) for r in rows]

    totals = {
        "billing": sum(r["billing"] or 0 for r in result),
        "receipt": sum(r["receipt"] or 0 for r in result),
        "expense": sum((r["salary"] or 0)+(r["direct"] or 0) for r in result),
        "count":   len(result),
    }
    return jsonify({"rows": result, "totals": totals})

# ── API: PROJECTS ─────────────────────────────────────────────────────────────
@app.route("/api/projects")
@login_required
def api_projects():
    """Returns per-project totals for the resolved period (FY/Month/Cumulative/All),
    plus lifetime (all-time) totals for reference. The 'period' totals are what the
    UI shows as the primary columns; lifetime is available for the expandable section."""
    args = {
        "pm": request.args.get("pm", ""),
        "group": request.args.get("group", ""),
        "client": request.args.get("client", ""),
        "search": request.args.get("search",""),
        "active": request.args.get("active","1"),
        "fy_start": request.args.get("fy_start", ""),
        "month": request.args.get("month", ""),
        "year": request.args.get("year", ""),
        "cumulative": request.args.get("cumulative", "1"),
    }
    return jsonify(compute_projects_summary(args))

def compute_projects_summary(args):
    """Plain function (no Flask request needed) so both the API route and the
    Excel export can produce IDENTICAL figures for the same period/filters."""
    pm     = args.get("pm", "")
    grp    = args.get("group", "")
    client = args.get("client", "")
    search = (args.get("search") or "").lower()
    active = args.get("active","1")

    period = resolve_period(args.get("fy_start",""), args.get("month",""),
                            args.get("year",""), args.get("cumulative","1"))

    sql = "SELECT p.* FROM projects p WHERE 1=1"
    params = []
    if active != "all": sql += " AND p.is_active=?"; params.append(int(active))
    if pm:     sql += " AND p.project_manager=?"; params.append(pm)
    if grp:    sql += " AND p.project_group=?";   params.append(grp)
    if client: sql += " AND p.client_name=?";     params.append(client)
    sql += " ORDER BY p.project_manager, p.sheet_ref"

    rows = query(sql, params)
    result = []

    for r in rows:
        d = dict(r)
        pid = r["id"]
        if search and search not in str(d.get("job_no","")).lower() \
                   and search not in str(d.get("project_name","")).lower() \
                   and search not in str(d.get("sheet_ref","")).lower():
            continue

        # LIFETIME totals (all transactions, start to date) — always available
        life = query("""
            SELECT
                SUM(CASE WHEN txn_type='BILLING' THEN amount ELSE 0 END) billing,
                SUM(CASE WHEN txn_type='RECEIPT' THEN amount_received ELSE 0 END) receipt,
                SUM(CASE WHEN txn_type='EXPENSE' THEN salary_actual ELSE 0 END) salary,
                SUM(CASE WHEN txn_type='EXPENSE' THEN direct_actual ELSE 0 END) direct
            FROM transactions WHERE project_id=?
        """, (pid,), one=True)
        billing = float(life["billing"] or 0) if life else 0
        receipt = float(life["receipt"] or 0) if life else 0
        salary  = float(life["salary"]  or 0) if life else 0
        direct  = float(life["direct"]  or 0) if life else 0

        # PERIOD totals (the resolved FY/Month/Cumulative window) — primary display figures
        period_row = query(f"""
            SELECT
                SUM(CASE WHEN txn_type='BILLING' THEN amount ELSE 0 END) billing,
                SUM(CASE WHEN txn_type='RECEIPT' THEN amount_received ELSE 0 END) receipt,
                SUM(CASE WHEN txn_type='EXPENSE' THEN salary_actual ELSE 0 END) salary,
                SUM(CASE WHEN txn_type='EXPENSE' THEN direct_actual ELSE 0 END) direct
            FROM transactions WHERE project_id=? AND {period['sql_cond']}
        """, [pid] + period["sql_params"], one=True)
        p_billing = float(period_row["billing"] or 0) if period_row else 0
        p_receipt = float(period_row["receipt"] or 0) if period_row else 0
        p_salary  = float(period_row["salary"]  or 0) if period_row else 0
        p_direct  = float(period_row["direct"]  or 0) if period_row else 0

        # If a period filter is active (not 'all'), only include projects with activity in it
        if period["mode"] != "all" and p_billing==0 and p_receipt==0 and p_salary==0 and p_direct==0:
            continue

        # Receivable as-of the period's upper boundary (or lifetime if 'all')
        if period["upto_month"] and period["upto_year"]:
            recv_row = query("""
                SELECT
                    SUM(CASE WHEN txn_type='BILLING' THEN amount ELSE 0 END) b,
                    SUM(CASE WHEN txn_type='RECEIPT' THEN amount_received ELSE 0 END) r
                FROM transactions WHERE project_id=?
                AND (txn_year < ? OR (txn_year=? AND txn_month<=?))
            """, (pid, period["upto_year"], period["upto_year"], period["upto_month"]), one=True)
            recv_upto_b = float(recv_row["b"] or 0) if recv_row else 0
            recv_upto_r = float(recv_row["r"] or 0) if recv_row else 0
        else:
            recv_upto_b, recv_upto_r = billing, receipt

        lb = query("SELECT MAX(invoice_date) ld FROM transactions WHERE project_id=? AND txn_type='BILLING'", (pid,), one=True)
        lr = query("SELECT MAX(cheque_date) ld FROM transactions WHERE project_id=? AND txn_type='RECEIPT'", (pid,), one=True)
        d["last_billing"]  = lb["ld"][:7] if lb and lb["ld"] else "—"
        d["last_receipt"]  = lr["ld"][:7] if lr and lr["ld"] else "—"

        # Lifetime (kept for reference / expandable panel)
        d["billing_upto"] = billing
        d["receipt_upto"] = receipt
        d["salary_upto"]  = salary
        d["direct_upto"]  = direct
        d["receivable"]   = billing - receipt
        d["pl_billing"]   = billing - (salary+direct)
        d["pl_receipt"]   = receipt - (salary+direct)

        # Period (primary display columns)
        d["period_billing"]    = p_billing
        d["period_receipt"]    = p_receipt
        d["period_salary"]     = p_salary
        d["period_direct"]     = p_direct
        d["period_expense"]    = p_salary + p_direct
        d["period_pl_billing"] = p_billing - (p_salary+p_direct)
        d["period_pl_receipt"] = p_receipt - (p_salary+p_direct)
        d["period_receivable"] = recv_upto_b - recv_upto_r

        # legacy aliases some older frontend code may still reference
        d["fy_billing"] = p_billing
        d["fy_receipt"] = p_receipt
        d["fy_salary"]  = p_salary
        d["fy_direct"]  = p_direct
        d["fy_receivable"] = d["period_receivable"]
        d["fy_pl_billing"] = d["period_pl_billing"]

        result.append(d)

    totals = {
        "billing":    sum(float(r.get("period_billing") or 0) for r in result),
        "receipt":    sum(float(r.get("period_receipt") or 0) for r in result),
        "expense":    sum(float(r.get("period_expense") or 0) for r in result),
        "receivable": sum(float(r.get("period_receivable") or 0) for r in result),
        "pl_billing": sum(float(r.get("period_pl_billing") or 0) for r in result),
        "lifetime_billing":    sum(float(r.get("billing_upto") or 0) for r in result),
        "lifetime_receipt":    sum(float(r.get("receipt_upto") or 0) for r in result),
        "lifetime_receivable": sum(float(r.get("receivable")   or 0) for r in result),
        "count":      len(result),
    }
    return {"projects": result, "totals": totals,
            "current_fy_start": get_current_fy()[0],
            "period_label": period["label"], "period_mode": period["mode"]}

@app.route("/api/clients")
@login_required
def api_clients():
    """Plain list of client names for dropdowns. Sources from clients_master first,
    falls back to any client_name found on projects (covers data entered before
    the master list existed)."""
    master = query("SELECT full_name FROM clients_master WHERE is_active=1 ORDER BY full_name")
    names = [r["full_name"] for r in master]
    legacy = query("SELECT DISTINCT client_name FROM projects WHERE client_name IS NOT NULL AND client_name != '' ORDER BY client_name")
    for r in legacy:
        if r["client_name"] not in names:
            names.append(r["client_name"])
    return jsonify(sorted(names))

@app.route("/api/clients/master")
@login_required
def api_clients_master_list():
    rows = query("SELECT * FROM clients_master ORDER BY full_name")
    return jsonify([dict(r) for r in rows])

@app.route("/api/clients/master", methods=["POST"])
@login_required
def api_clients_master_create():
    if session.get("role") != "admin":
        return jsonify({"error":"Admin only"}), 403
    d = request.get_json()
    name = (d.get("full_name") or "").strip()
    if not name:
        return jsonify({"error":"Client name is required"}), 400
    try:
        cid = execute("INSERT INTO clients_master (full_name, short_name, ntn_no) VALUES (?,?,?)",
                      (name, d.get("short_name"), d.get("ntn_no")))
    except Exception:
        return jsonify({"error": "A client with this name already exists"}), 400
    return jsonify({"ok": True, "id": cid})

@app.route("/api/clients/master/<int:cid>", methods=["PUT"])
@login_required
def api_clients_master_update(cid):
    """Updates the master record only. Historical bookings (transactions/projects
    that already stored this client's name as plain text) are NOT rewritten —
    only future bookings will use the new short_name/NTN. Renaming full_name
    here changes how the client appears in NEW dropdowns going forward; existing
    records keep showing whatever name was saved at the time."""
    if session.get("role") != "admin":
        return jsonify({"error":"Admin only"}), 403
    d = request.get_json()
    execute("""UPDATE clients_master SET full_name=?, short_name=?, ntn_no=?, is_active=?,
               updated_at=date('now') WHERE id=?""",
            (d.get("full_name"), d.get("short_name"), d.get("ntn_no"),
             int(d.get("is_active", 1)), cid))
    return jsonify({"ok": True})

@app.route("/api/clients/master/<int:cid>", methods=["DELETE"])
@login_required
def api_clients_master_delete(cid):
    if session.get("role") != "admin":
        return jsonify({"error":"Admin only"}), 403
    execute("DELETE FROM clients_master WHERE id=?", (cid,))
    return jsonify({"ok": True})

@app.route("/api/pms/master")
@login_required
def api_pm_master_list():
    rows = query("SELECT * FROM pm_master ORDER BY full_name")
    return jsonify([dict(r) for r in rows])

@app.route("/api/pms/master", methods=["POST"])
@login_required
def api_pm_master_create():
    if session.get("role") != "admin":
        return jsonify({"error":"Admin only"}), 403
    d = request.get_json()
    name = (d.get("full_name") or "").strip()
    if not name:
        return jsonify({"error":"PM name is required"}), 400
    try:
        pid = execute("INSERT INTO pm_master (full_name, employee_code, designation) VALUES (?,?,?)",
                      (name, d.get("employee_code"), d.get("designation")))
    except Exception:
        return jsonify({"error": "A PM with this name already exists"}), 400
    return jsonify({"ok": True, "id": pid})

@app.route("/api/pms/master/<int:pid>", methods=["PUT"])
@login_required
def api_pm_master_update(pid):
    """Same forward-only behavior as clients: editing employee_code/designation/name
    here does not rewrite any project_manager text already saved on past projects
    or transactions. Use 'Reassign Projects' separately to move existing projects
    to a different PM."""
    if session.get("role") != "admin":
        return jsonify({"error":"Admin only"}), 403
    d = request.get_json()
    execute("""UPDATE pm_master SET full_name=?, employee_code=?, designation=?, is_active=?,
               updated_at=date('now') WHERE id=?""",
            (d.get("full_name"), d.get("employee_code"), d.get("designation"),
             int(d.get("is_active", 1)), pid))
    return jsonify({"ok": True})

@app.route("/api/pms/master/<int:pid>", methods=["DELETE"])
@login_required
def api_pm_master_delete(pid):
    if session.get("role") != "admin":
        return jsonify({"error":"Admin only"}), 403
    execute("DELETE FROM pm_master WHERE id=?", (pid,))
    return jsonify({"ok": True})

# ── Tax Rates Master API ───────────────────────────────────────────────────────
@app.route("/api/tax_rates/master")
@login_required
def api_tax_rates_master_list():
    rows = query("SELECT * FROM tax_rates_master ORDER BY tax_name")
    return jsonify([dict(r) for r in rows])

@app.route("/api/tax_rates/master", methods=["POST"])
@login_required
def api_tax_rates_master_create():
    if session.get("role") != "admin":
        return jsonify({"error":"Admin only"}), 403
    d = request.get_json()
    name = (d.get("tax_name") or "").strip()
    rate = float(d.get("rate_percent") or 0)
    if not name:
        return jsonify({"error": "Tax name is required"}), 400
    try:
        tid = execute("INSERT INTO tax_rates_master (tax_name, rate_percent) VALUES (?,?)", (name, rate))
        return jsonify({"ok": True, "id": tid})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/tax_rates/master/<int:tid>", methods=["PUT"])
@login_required
def api_tax_rates_master_update(tid):
    if session.get("role") != "admin":
        return jsonify({"error":"Admin only"}), 403
    d = request.get_json()
    name = (d.get("tax_name") or "").strip()
    rate = float(d.get("rate_percent") or 0)
    active = int(d.get("is_active") or 1)
    if not name:
        return jsonify({"error": "Tax name is required"}), 400
    execute("""UPDATE tax_rates_master SET tax_name=?, rate_percent=?, is_active=?, updated_at=date('now')
               WHERE id=?""", (name, rate, active, tid))
    return jsonify({"ok": True})

@app.route("/api/tax_rates/master/<int:tid>", methods=["DELETE"])
@login_required
def api_tax_rates_master_delete(tid):
    if session.get("role") != "admin":
        return jsonify({"error":"Admin only"}), 403
    execute("DELETE FROM tax_rates_master WHERE id=?", (tid,))
    return jsonify({"ok": True})

@app.route("/api/projects/reassign_pm", methods=["POST"])
@login_required
def api_reassign_pm():
    """Bulk-move a set of projects (or ALL projects currently under old_pm) to a new PM.
    This DOES rewrite projects.project_manager going forward (the whole point of
    this endpoint), but never touches historical transaction rows — past invoices/
    receipts/expenses keep whatever PM name was true at the time they were booked,
    which is the correct accounting behavior."""
    if session.get("role") != "admin":
        return jsonify({"error":"Admin only"}), 403
    d = request.get_json()
    new_pm = d.get("new_pm")
    project_ids = d.get("project_ids")  # list of ids, OR None to mean "all under old_pm"
    old_pm = d.get("old_pm")
    if not new_pm:
        return jsonify({"error": "New PM is required"}), 400
    if project_ids:
        placeholders = ",".join("?" * len(project_ids))
        execute(f"UPDATE projects SET project_manager=?, updated_at=date('now') WHERE id IN ({placeholders})",
                [new_pm] + project_ids)
        count = len(project_ids)
    elif old_pm:
        cnt = query("SELECT COUNT(*) c FROM projects WHERE project_manager=?", (old_pm,), one=True)
        count = cnt["c"] if cnt else 0
        execute("UPDATE projects SET project_manager=?, updated_at=date('now') WHERE project_manager=?",
                (new_pm, old_pm))
    else:
        return jsonify({"error": "Provide either project_ids or old_pm"}), 400
    return jsonify({"ok": True, "count": count})

# ── Project multi-client support ───────────────────────────────────────────────
@app.route("/api/projects/<int:pid>/clients")
@login_required
def api_project_clients_list(pid):
    rows = query("SELECT * FROM project_clients WHERE project_id=? ORDER BY id", (pid,))
    return jsonify([dict(r) for r in rows])

@app.route("/api/projects/<int:pid>/clients", methods=["POST"])
@login_required
def api_project_clients_add(pid):
    if session.get("role") != "admin":
        return jsonify({"error":"Admin only"}), 403
    d = request.get_json()
    name = (d.get("client_name") or "").strip()
    if not name:
        return jsonify({"error": "Client name required"}), 400
    cid = execute("INSERT INTO project_clients (project_id, client_name, client_ntn) VALUES (?,?,?)",
                  (pid, name, d.get("client_ntn")))
    execute("UPDATE projects SET has_multiple_clients=1 WHERE id=?", (pid,))
    return jsonify({"ok": True, "id": cid})

@app.route("/api/projects/clients/<int:row_id>", methods=["DELETE"])
@login_required
def api_project_clients_delete(row_id):
    if session.get("role") != "admin":
        return jsonify({"error":"Admin only"}), 403
    row = query("SELECT * FROM project_clients WHERE id=?", (row_id,), one=True)
    if row:
        execute("DELETE FROM project_clients WHERE id=?", (row_id,))
        remaining = query("SELECT COUNT(*) c FROM project_clients WHERE project_id=?", (row["project_id"],), one=True)
        if remaining and remaining["c"] == 0:
            execute("UPDATE projects SET has_multiple_clients=0 WHERE id=?", (row["project_id"],))
    return jsonify({"ok": True})

@app.route("/api/list/<entity>")
@login_required
def api_period_list(entity):
    """
    Universal filtered list endpoint backing the Invoices / Receipts / Expenses /
    Cheques / Performa sidebar pages. Same period engine as Dashboard/Projects.
    entity: 'invoices' | 'receipts' | 'expenses' | 'cheques' | 'performa'
    """
    args = {
        "fy_start": request.args.get("fy_start", ""),
        "month":    request.args.get("month", ""),
        "year":     request.args.get("year", ""),
        "cumulative": request.args.get("cumulative", "1"),
        "pm":     request.args.get("pm", ""),
        "group":  request.args.get("group", ""),
        "client": request.args.get("client", ""),
        "job":    request.args.get("job", ""),
    }
    result = compute_period_list(entity, args)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)

def compute_period_list(entity, args):
    """Plain (non-Flask-route) function so it can be called both by the API route
    and directly by the Excel export endpoint without HTTP request-context tricks."""
    fy_start_arg = args.get("fy_start", "")
    month_arg    = args.get("month", "")
    year_arg     = args.get("year", "")
    cumulative   = args.get("cumulative", "1")
    pm     = args.get("pm", "")
    grp    = args.get("group", "")
    client = args.get("client", "")
    job    = args.get("job", "")

    if entity == "cheques":
        period_c = resolve_period(fy_start_arg, month_arg, year_arg, cumulative, alias="c.")
        sql = f"""SELECT c.*, p.project_manager, p.project_group, p.client_name 
                  FROM cheques c 
                  LEFT JOIN transactions t ON c.cheque_no = t.cheque_no
                  LEFT JOIN projects p ON t.project_id = p.id
                  WHERE {period_c['sql_cond']}"""
        params = list(period_c["sql_params"])
        if pm:     sql += " AND (p.project_manager=? OR c.client_name=?)"; params.extend([pm, pm])
        if grp:    sql += " AND p.project_group=?";   params.append(grp)
        if client: sql += " AND (p.client_name=? OR c.client_name=?)"; params.extend([client, client])
        sql += " GROUP BY c.id ORDER BY c.cheque_date DESC, c.id DESC"
        rows = query(sql, params)
        result = []
        for r in rows:
            d = dict(r)
            alloc = query("SELECT COALESCE(SUM(total_amount),0) a FROM performas WHERE cheque_id=?", (r["id"],), one=True)
            d["allocated"] = float(alloc["a"] or 0) if alloc else 0
            d["remaining"] = float(r["amount"] or 0) - d["allocated"]
            result.append(d)
        totals = {"count": len(result),
                  "amount": sum(r["amount"] or 0 for r in result),
                  "allocated": sum(r["allocated"] for r in result),
                  "remaining": sum(r["remaining"] for r in result)}
        return {"rows": result, "totals": totals, "period_label": period_c["label"]}

    if entity == "performa":
        period_p = resolve_period(fy_start_arg, month_arg, year_arg, cumulative, alias="p.")
        sql = f"""SELECT p.*, c.cheque_no, c.cheque_date, c.amount as cheque_amount,
                         prj.project_manager, prj.project_group, prj.client_name
                  FROM performas p 
                  LEFT JOIN cheques c ON c.id=p.cheque_id
                  LEFT JOIN performa_lines pl ON pl.performa_id = p.id
                  LEFT JOIN projects prj ON pl.project_id = prj.id
                  WHERE {period_p['sql_cond']}"""
        params = list(period_p["sql_params"])
        if pm:     sql += " AND prj.project_manager=?"; params.append(pm)
        if grp:    sql += " AND prj.project_group=?";   params.append(grp)
        if client: sql += " AND (prj.client_name=? OR pl.client_name=?)"; params.extend([client, client])
        sql += " GROUP BY p.id ORDER BY p.created_at DESC"
        rows = query(sql, params)
        result = [dict(r) for r in rows]
        totals = {"count": len(result), "amount": sum(r["total_amount"] or 0 for r in result)}
        return {"rows": result, "totals": totals, "period_label": period_p["label"]}

    # invoices / receipts / expenses -> transactions table
    type_map = {"invoices":"BILLING", "receipts":"RECEIPT", "expenses":"EXPENSE"}
    if entity not in type_map:
        return {"error": "Unknown entity"}
    txn_type = type_map[entity]
    period = resolve_period(fy_start_arg, month_arg, year_arg, cumulative, alias="t.")

    sql = f"""SELECT t.*, p.sheet_ref, p.job_no, p.project_name, p.project_manager,
                     p.client_name, p.project_group, p.client_ntn
              FROM transactions t JOIN projects p ON p.id = t.project_id
              WHERE t.txn_type=? AND {period['sql_cond']}"""
    params = [txn_type] + list(period["sql_params"])
    if pm:     sql += " AND p.project_manager=?"; params.append(pm)
    if grp:    sql += " AND p.project_group=?";   params.append(grp)
    if client: sql += " AND (p.client_name=? OR p.client_ntn=?)"; params.extend([client, client])
    if job:    sql += " AND p.job_no LIKE ?";      params.append(f"%{job}%")
    sql += " ORDER BY t.txn_year, t.txn_month, p.project_manager, p.sheet_ref, t.id"

    rows = query(sql, params)
    result = [dict(r) for r in rows]

    if txn_type == "BILLING":
        totals = {"count": len(result),
                  "amount": sum(r["amount"] or 0 for r in result),
                  "tax": sum(r["tax_amount"] or 0 for r in result),
                  "gross": sum(r["gross_amount"] or 0 for r in result)}
    elif txn_type == "RECEIPT":
        totals = {"count": len(result),
                  "cheque_amount": sum(r["cheque_amount"] or 0 for r in result),
                  "amount_received": sum(r["amount_received"] or 0 for r in result)}
    else:
        totals = {"count": len(result),
                  "salary": sum(r["salary_actual"] or 0 for r in result),
                  "direct": sum(r["direct_actual"] or 0 for r in result),
                  "total": sum((r["salary_actual"] or 0)+(r["direct_actual"] or 0) for r in result)}

    return {"rows": result, "totals": totals, "period_label": period["label"]}

@app.route("/api/projects", methods=["POST"])
@login_required
def api_project_create():
    if session.get("role") != "admin":
        return jsonify({"error":"Admin only"}), 403
    d = request.get_json()
    pid = execute("""
        INSERT INTO projects (sheet_ref,job_no,project_name,client_name,
            project_manager,project_group,comm_date,comp_date,amendment,
            duration_months,nespak_fee_mil,salary_cost_est,direct_cost_est,remarks)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (d.get("sheet_ref"),d.get("job_no"),d["project_name"],d.get("client_name"),
          d["project_manager"],d.get("project_group","GENERAL"),
          d.get("comm_date"),d.get("comp_date"),d.get("amendment","None"),
          float(d.get("duration_months") or 0),float(d.get("nespak_fee_mil") or 0),
          float(d.get("salary_cost_est") or 0),float(d.get("direct_cost_est") or 0),
          d.get("remarks")))
    return jsonify({"ok": True, "id": pid})

@app.route("/api/projects/<int:pid>", methods=["PUT"])
@login_required
def api_project_update(pid):
    if session.get("role") != "admin":
        return jsonify({"error":"Admin only"}), 403
    d = request.get_json()
    execute("""UPDATE projects SET sheet_ref=?,job_no=?,project_name=?,client_name=?,
        project_manager=?,project_group=?,comm_date=?,comp_date=?,amendment=?,
        duration_months=?,nespak_fee_mil=?,salary_cost_est=?,direct_cost_est=?,
        remarks=?,is_active=?,updated_at=date('now') WHERE id=?""",
        (d.get("sheet_ref"),d.get("job_no"),d["project_name"],d.get("client_name"),
         d["project_manager"],d.get("project_group","GENERAL"),
         d.get("comm_date"),d.get("comp_date"),d.get("amendment","None"),
         float(d.get("duration_months") or 0),float(d.get("nespak_fee_mil") or 0),
         float(d.get("salary_cost_est") or 0),float(d.get("direct_cost_est") or 0),
         d.get("remarks"),int(d.get("is_active",1)),pid))
    return jsonify({"ok": True})

@app.route("/api/projects/<int:pid>")
@login_required
def api_project_detail(pid):
    p = query("SELECT * FROM projects WHERE id=?", (pid,), one=True)
    if not p: return jsonify({"error":"Not found"}), 404
    txns = query("SELECT * FROM transactions WHERE project_id=? ORDER BY txn_year,txn_month,id", (pid,))
    snaps= query("SELECT * FROM monthly_snapshot WHERE project_id=? ORDER BY snap_year,snap_month", (pid,))
    return jsonify({"project": dict(p),
                    "transactions": [dict(t) for t in txns],
                    "snapshots": [dict(s) for s in snaps]})

# ── API: TRANSACTIONS ─────────────────────────────────────────────────────────
@app.route("/api/transactions", methods=["POST"])
@login_required
def api_txn_create():
    if session.get("role") != "admin":
        return jsonify({"error":"Admin only"}), 403
    d = request.get_json()
    pid   = int(d["project_id"])
    month = int(d["month"])
    year  = int(d["year"])
    typ   = d["txn_type"]

    # Duplicate check
    existing = query(
        "SELECT COUNT(*) c FROM transactions WHERE project_id=? AND txn_month=? AND txn_year=? AND txn_type=?",
        (pid,month,year,typ), one=True)
    if existing["c"] > 0 and not d.get("confirmed"):
        return jsonify({"duplicate": True,
                        "count": existing["c"],
                        "message": f"There are already {existing['c']} {typ} entries for this project in this month. Confirm to add another."})

    # Attachment not-provided warning (non-blocking, just informs frontend)
    attach_name = d.get("attachment_name") or None
    attach_skip = 1 if (not attach_name and d.get("attachment_skipped")) else 0
    if not attach_name and not d.get("attachment_skipped") and not d.get("confirmed_no_attachment"):
        return jsonify({"no_attachment": True,
                        "message": "No file attached for this entry. Continue without attaching?"})

    txn_id = None
    if typ == "BILLING":
        p = query("SELECT * FROM projects WHERE id=?", (pid,), one=True)
        job_no = p["job_no"] or "0000"
        fy = get_fy(month, year)
        seq = get_next_invoice_no(pid)
        inv_no = f"{INVOICE_PREFIX}/{job_no}/{fy}/{seq:02d}"
        amt    = float(d.get("amount") or 0)
        rate   = float(d.get("tax_rate") or 0)
        tax_a  = amt * rate / 100
        gross  = amt + tax_a
        txn_id = execute("""INSERT INTO transactions
            (project_id,txn_month,txn_year,txn_type,amount,
             invoice_no,invoice_date,tax_type,tax_rate,tax_amount,gross_amount,
             description,attachment_name,attachment_skipped)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (pid,month,year,typ,amt,inv_no,d.get("invoice_date"),
             d.get("tax_type"),rate,tax_a,gross,d.get("description"),
             attach_name, attach_skip))

    elif typ == "RECEIPT":
        chq  = float(d.get("cheque_amount") or 0)
        it   = float(d.get("it_adjustable")    or 0)
        pra  = float(d.get("pra_adjustable")   or 0)
        oa   = float(d.get("other_adjustable") or 0)
        st_r = float(d.get("st_received")      or 0)
        st_d = float(d.get("st_deducted")      or 0)
        est_d= float(d.get("extra_st_deducted")or 0)
        ona  = float(d.get("other_non_adj")    or 0)
        # Amount received = cheque - (ST received + ST deducted + Extra ST deducted + other non-adj) + adjustable (IT+PRA+Other)
        received = chq - st_r - st_d - est_d + it + pra + oa - ona
        txn_id = execute("""INSERT INTO transactions
            (project_id,txn_month,txn_year,txn_type,amount,
             cheque_no,cheque_date,cheque_amount,
             it_adjustable,pra_adjustable,other_adjustable,
             st_received,st_deducted,extra_st_deducted,other_non_adj,amount_received,
             description,attachment_name,attachment_skipped)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (pid,month,year,typ,received,
             d.get("cheque_no"),d.get("cheque_date"),chq,
             it,pra,oa,st_r,st_d,est_d,ona,received,d.get("description"),
             attach_name, attach_skip))

    elif typ == "EXPENSE":
        sal  = float(d.get("salary_actual")  or 0)
        dir_ = float(d.get("direct_actual")  or 0)
        txn_id = execute("""INSERT INTO transactions
            (project_id,txn_month,txn_year,txn_type,amount,
             salary_actual,direct_actual,description)
            VALUES (?,?,?,?,?,?,?,?)""",
            (pid,month,year,typ,sal+dir_,sal,dir_,d.get("description")))

    if txn_id:
        rebuild_snapshot(pid, month, year)
    return jsonify({"ok": True, "id": txn_id})

@app.route("/api/upload", methods=["POST"])
@login_required
def api_upload():
    """Upload a file attachment (invoice/receipt copy). Returns saved filename."""
    if session.get("role") != "admin":
        return jsonify({"error":"Admin only"}), 403
    if "file" not in request.files:
        return jsonify({"error":"No file provided"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"error":"No file selected"}), 400
    ext = os.path.splitext(f.filename)[1]
    safe_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{f.filename.replace(' ','_')}"
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    path = os.path.join(UPLOAD_FOLDER, safe_name)
    f.save(path)
    return jsonify({"ok": True, "filename": safe_name, "original_name": f.filename})

@app.route("/api/transactions/<int:tid>", methods=["DELETE"])
@login_required
def api_txn_delete(tid):
    if session.get("role") != "admin":
        return jsonify({"error":"Admin only"}), 403
    row = query("SELECT * FROM transactions WHERE id=?", (tid,), one=True)
    if row:
        execute("DELETE FROM transactions WHERE id=?", (tid,))
        rebuild_snapshot(row["project_id"], row["txn_month"], row["txn_year"])
    return jsonify({"ok": True})

@app.route("/api/transactions/<int:tid>", methods=["PUT"])
@login_required
def api_txn_update(tid):
    if session.get("role") != "admin":
        return jsonify({"error":"Admin only"}), 403
    d   = request.get_json()
    row = query("SELECT * FROM transactions WHERE id=?", (tid,), one=True)
    if not row: return jsonify({"error":"Not found"}), 404
    typ = row["txn_type"]
    if typ == "BILLING":
        amt   = float(d.get("amount") or row["amount"])
        rate  = float(d.get("tax_rate") or row["tax_rate"] or 0)
        tax_a = amt * rate / 100
        execute("UPDATE transactions SET amount=?,tax_rate=?,tax_amount=?,gross_amount=?,invoice_date=?,description=?,updated_at=date('now') WHERE id=?",
                (amt,rate,tax_a,amt+tax_a,d.get("invoice_date",row["invoice_date"]),d.get("description",row["description"]),tid))
    elif typ == "RECEIPT":
        chq  = float(d.get("cheque_amount") or row["cheque_amount"] or 0)
        it   = float(d.get("it_adjustable")    or row["it_adjustable"]    or 0)
        pra  = float(d.get("pra_adjustable")   or row["pra_adjustable"]   or 0)
        oa   = float(d.get("other_adjustable") or row["other_adjustable"] or 0)
        st_r = float(d.get("st_received")      or row["st_received"]      or 0)
        st_d = float(d.get("st_deducted")      or row["st_deducted"]      or 0)
        est_d= float(d.get("extra_st_deducted")or row["extra_st_deducted"]or 0)
        ona  = float(d.get("other_non_adj")    or row["other_non_adj"]    or 0)
        received = chq - st_r - st_d - est_d + it + pra + oa - ona
        execute("""UPDATE transactions SET cheque_amount=?,it_adjustable=?,pra_adjustable=?,
            other_adjustable=?,st_received=?,st_deducted=?,extra_st_deducted=?,other_non_adj=?,
            amount_received=?,amount=?,updated_at=date('now') WHERE id=?""",
                (chq,it,pra,oa,st_r,st_d,est_d,ona,received,received,tid))
    elif typ == "EXPENSE":
        sal  = float(d.get("salary_actual") or row["salary_actual"] or 0)
        dir_ = float(d.get("direct_actual") or row["direct_actual"] or 0)
        execute("UPDATE transactions SET salary_actual=?,direct_actual=?,amount=?,updated_at=date('now') WHERE id=?",
                (sal,dir_,sal+dir_,tid))
    rebuild_snapshot(row["project_id"], row["txn_month"], row["txn_year"])
    return jsonify({"ok": True})

@app.route("/api/transactions/recent")
@login_required
def api_recent_txns():
    typ = request.args.get("type","")
    sql = """SELECT t.*,p.job_no,p.project_name,p.sheet_ref
             FROM transactions t JOIN projects p ON p.id=t.project_id"""
    params = []
    if typ: sql += " WHERE t.txn_type=?"; params.append(typ)
    sql += " ORDER BY t.txn_year DESC,t.txn_month DESC,t.id DESC LIMIT 150"
    rows = query(sql, params)
    return jsonify([dict(r) for r in rows])

@app.route("/api/transactions/month")
@login_required
def api_month_txns():
    month = int(request.args.get("month", date.today().month))
    year  = int(request.args.get("year",  date.today().year))
    typ   = request.args.get("type","")
    pm    = request.args.get("pm","")
    sql = """SELECT t.*,p.job_no,p.project_name,p.sheet_ref,p.project_manager
             FROM transactions t JOIN projects p ON p.id=t.project_id
             WHERE t.txn_month=? AND t.txn_year=?"""
    params = [month,year]
    if typ: sql+=" AND t.txn_type=?"; params.append(typ)
    if pm:  sql+=" AND p.project_manager=?"; params.append(pm)
    sql+=" ORDER BY p.project_manager,p.sheet_ref,t.id"
    rows = query(sql,params)
    return jsonify([dict(r) for r in rows])

# ── API: CHEQUES ───────────────────────────────────────────────────────────────
@app.route("/api/cheques")
@login_required
def api_cheques_list():
    month = request.args.get("month","")
    year  = request.args.get("year","")
    status= request.args.get("status","")
    sql = "SELECT * FROM cheques WHERE 1=1"
    params = []
    if month: sql += " AND txn_month=?"; params.append(int(month))
    if year:  sql += " AND txn_year=?";  params.append(int(year))
    if status:sql += " AND status=?";    params.append(status)
    sql += " ORDER BY cheque_date DESC, id DESC"
    rows = query(sql, params)
    result = []
    for r in rows:
        d = dict(r)
        # how much of this cheque has been allocated to performas already
        alloc = query("SELECT COALESCE(SUM(total_amount),0) a FROM performas WHERE cheque_id=?", (r["id"],), one=True)
        d["allocated"] = float(alloc["a"] or 0) if alloc else 0
        d["remaining"] = float(r["amount"] or 0) - d["allocated"]
        result.append(d)
    return jsonify(result)

@app.route("/api/cheques/<int:cid>", methods=["GET"])
@login_required
def api_cheques_detail(cid):
    """Return full details of a single cheque."""
    chq = query("SELECT * FROM cheques WHERE id=?", (cid,), one=True)
    if not chq:
        return jsonify({"error": "Cheque not found"}), 404
    d = dict(chq)
    # how much of this cheque has been allocated to performas already
    alloc = query("SELECT COALESCE(SUM(total_amount),0) a FROM performas WHERE cheque_id=?", (cid,), one=True)
    d["allocated"] = float(alloc["a"] or 0) if alloc else 0
    d["remaining"] = float(chq["amount"] or 0) - d["allocated"]
    return jsonify(d)

@app.route("/api/cheques", methods=["POST"])
@login_required
def api_cheques_create():
    if session.get("role") != "admin":
        return jsonify({"error":"Admin only"}), 403
    d = request.get_json()
    cid = execute("""INSERT INTO cheques (cheque_no,cheque_date,amount,client_name,bank_name,memo_no,memo_date,remarks,txn_month,txn_year,fy,attachment_path)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (d.get("cheque_no"), d.get("cheque_date"), float(d.get("amount") or 0),
         d.get("client_name"), d.get("bank_name"), d.get("memo_no"), d.get("memo_date"),
         d.get("remarks"), int(d.get("month")), int(d.get("year")), d.get("fy"),
         d.get("attachment_path")))
    return jsonify({"ok": True, "id": cid})

@app.route("/api/cheques/<int:cid>", methods=["PUT"])
@login_required
def api_cheques_update(cid):
    if session.get("role") != "admin":
        return jsonify({"error":"Admin only"}), 403
    d = request.get_json()
    fields = []
    params = []
    for k in ["cheque_no", "cheque_date", "amount", "client_name", "bank_name", "memo_no", "memo_date", "remarks", "fy", "attachment_path"]:
        if k in d:
            fields.append(f"{k}=?")
            params.append(d[k] if k != "amount" else float(d[k] or 0))
    if not fields:
        return jsonify({"error": "No fields to update"}), 400
    params.append(cid)
    execute(f"UPDATE cheques SET {','.join(fields)} WHERE id=?", params)
    return jsonify({"ok": True})

@app.route("/api/cheques/<int:cid>", methods=["DELETE"])
@login_required
def api_cheques_delete(cid):
    if session.get("role") != "admin":
        return jsonify({"error":"Admin only"}), 403
    used = query("SELECT COUNT(*) c FROM performas WHERE cheque_id=?", (cid,), one=True)
    if used and used["c"] > 0:
        return jsonify({"error": "This cheque is already used in a Performa. Delete the Performa first."}), 400
    execute("DELETE FROM cheques WHERE id=?", (cid,))
    return jsonify({"ok": True})

# ── API: PERFORMA ──────────────────────────────────────────────────────────────
@app.route("/api/performa/pending_invoices")
@login_required
def api_pending_invoices():
    """Return invoices for a project that are NOT fully received yet (pending balance)."""
    pid = int(request.args.get("project_id"))
    invoices = query("""
        SELECT * FROM transactions WHERE project_id=? AND txn_type='BILLING'
        ORDER BY txn_year, txn_month, id
    """, (pid,))
    result = []
    for inv in invoices:
        gross = float(inv["gross_amount"] or 0)
        # sum of all performa_lines already linked to this invoice (cheque_share = amount applied)
        applied = query("""
            SELECT COALESCE(SUM(cheque_share + st_received + st_deducted + extra_st_deducted),0) a
            FROM performa_lines WHERE invoice_txn_id=?
        """, (inv["id"],), one=True)
        applied_amt = float(applied["a"] or 0) if applied else 0
        balance = gross - applied_amt
        if balance > 1:  # leave 1 rupee tolerance for rounding
            d = dict(inv)
            d["balance"] = balance
            d["already_applied"] = applied_amt
            result.append(d)
    return jsonify(result)

@app.route("/api/performa/invoice_details")
@login_required
def api_invoice_details():
    """Return details for a specific invoice."""
    invoice_id = int(request.args.get("invoice_id"))
    inv = query("SELECT * FROM transactions WHERE id=?", (invoice_id,), one=True)
    if not inv:
        return jsonify({"error": "Invoice not found"}), 404
    
    gross = float(inv["gross_amount"] or 0)
    applied = query("""
        SELECT COALESCE(SUM(cheque_share + st_received + st_deducted + extra_st_deducted),0) a
        FROM performa_lines WHERE invoice_txn_id=?
    """, (invoice_id,), one=True)
    applied_amt = float(applied["a"] or 0) if applied else 0
    balance = gross - applied_amt
    
    d = dict(inv)
    d["balance_amount"] = balance
    return jsonify(d)

@app.route("/api/performa", methods=["GET"])
@login_required
def api_performa_list():
    month = request.args.get("month","")
    year  = request.args.get("year","")
    sql = """SELECT p.*, c.cheque_no, c.cheque_date, c.amount as cheque_amount
             FROM performas p LEFT JOIN cheques c ON c.id = p.cheque_id WHERE 1=1"""
    params = []
    if month: sql += " AND p.txn_month=?"; params.append(int(month))
    if year:  sql += " AND p.txn_year=?";  params.append(int(year))
    sql += " ORDER BY p.created_at DESC"
    rows = query(sql, params)
    return jsonify([dict(r) for r in rows])

@app.route("/api/performa/<int:perf_id>")
@login_required
def api_performa_detail(perf_id):
    p = query("""SELECT p.*, c.cheque_no, c.cheque_date, c.amount as cheque_amount
                 FROM performas p LEFT JOIN cheques c ON c.id=p.cheque_id
                 WHERE p.id=?""", (perf_id,), one=True)
    if not p: return jsonify({"error":"Not found"}), 404
    lines = query("""SELECT pl.*, pr.job_no, pr.sheet_ref, pr.project_name, pr.project_manager
                      FROM performa_lines pl JOIN projects pr ON pr.id = pl.project_id
                      WHERE pl.performa_id=? ORDER BY pl.id""", (perf_id,))
    # Ensure all Table 2 fields are included
    return jsonify({"performa": dict(p), "lines": [dict(l) for l in lines]})

@app.route("/api/performa", methods=["POST"])
@login_required
def api_performa_create():
    """Create a Performa: book one cheque against multiple invoices across multiple jobs.
    Each line auto-creates a linked RECEIPT transaction for that job.
    
    CRITICAL: Receipt booking is JOB-WISE, not invoice-wise.
    - Invoice level = Detail layer only
    - Job subtotal level = Actual receipt booking layer
    - Cheque level = Deduction entry layer
    """
    if session.get("role") != "admin":
        return jsonify({"error":"Admin only"}), 403
    d = request.get_json()
    cheque_id = d.get("cheque_id")
    month = int(d["month"])
    year  = int(d["year"])
    lines = d.get("lines", [])
    # Get cheque-level deductions (entered once for the complete cheque)
    cheque_level = d.get("cheque_level_deductions", {})
    it_deducted = float(cheque_level.get("it_deducted") or 0)
    pra_fee = float(cheque_level.get("pra_fee") or 0)
    other_adjustable = float(cheque_level.get("other_adjustable") or 0)
    st_deducted = float(cheque_level.get("st_deducted") or 0)
    st_received = float(cheque_level.get("st_received") or 0)
    extra_st_deduction = float(cheque_level.get("extra_st_deduction") or 0)
    other_deduction = float(cheque_level.get("other_deduction") or 0)
    
    if not lines:
        return jsonify({"error": "No invoice lines provided"}), 400

    # ── Server-side validation: never trust client-only checks ───────────────
    for l in lines:
        inv_txn_id = l.get("invoice_txn_id")
        if not inv_txn_id:
            continue
        inv = query("SELECT * FROM transactions WHERE id=?", (inv_txn_id,), one=True)
        if not inv:
            return jsonify({"error": f"Invoice not found for line {l.get('invoice_no')}"}), 400
        gross = float(inv["gross_amount"] or 0)
        applied_before = query("""
            SELECT COALESCE(SUM(cheque_share + st_received + st_deducted + extra_st_deducted),0) a
            FROM performa_lines WHERE invoice_txn_id=?
        """, (inv_txn_id,), one=True)
        already = float(applied_before["a"] or 0) if applied_before else 0
        balance = gross - already
        this_line_amt = (float(l.get("cheque_share") or 0) + float(l.get("st_received") or 0) +
                          float(l.get("st_deducted") or 0) + float(l.get("extra_st_deducted") or 0))
        if this_line_amt > balance + 1:
            return jsonify({"error": f"Amount received for invoice {l.get('invoice_no')} "
                                      f"(Rs.{this_line_amt:,.2f}) exceeds its outstanding balance "
                                      f"(Rs.{balance:,.2f}). Saving blocked."}), 400

    if cheque_id:
        chq = query("SELECT * FROM cheques WHERE id=?", (cheque_id,), one=True)
        if chq:
            alloc = query("SELECT COALESCE(SUM(total_amount),0) a FROM performas WHERE cheque_id=?", (cheque_id,), one=True)
            already_alloc = float(alloc["a"] or 0) if alloc else 0
            chq_remaining = float(chq["amount"] or 0) - already_alloc
            new_total = sum(float(l.get("cheque_share") or 0) for l in lines)
            if new_total > chq_remaining + 1:
                return jsonify({"error": f"Total Job Allocation (Rs.{new_total:,.2f}) exceeds "
                                          f"Cheque's available amount (Rs.{chq_remaining:,.2f}). Saving blocked."}), 400

    # generate performa number
    fy = get_fy(month, year)
    cnt = query("SELECT COUNT(*) c FROM performas WHERE txn_month=? AND txn_year=?", (month,year), one=True)
    perf_no = f"PERF/{fy}/{(cnt['c'] if cnt else 0)+1:03d}"

    total = sum(float(l.get("cheque_share") or 0) for l in lines)
    perf_id = execute("""INSERT INTO performas (performa_no, cheque_id, txn_month, txn_year, total_amount)
        VALUES (?,?,?,?,?)""", (perf_no, cheque_id, month, year, total))

    # Group lines by job for JOB-WISE receipt booking
    from collections import defaultdict
    job_lines = defaultdict(list)
    for l in lines:
        pid = int(l["project_id"])
        job_lines[pid].append(l)
    
    # Create JOB-WISE receipt bookings (NOT invoice-wise)
    for pid, job_lns in job_lines.items():
        # Sum up all values for this job
        job_cheque_share = sum(float(ln.get("cheque_share") or 0) for ln in job_lns)
        job_st_r = sum(float(ln.get("st_received") or 0) for ln in job_lns)
        job_st_d = sum(float(ln.get("st_deducted") or 0) for ln in job_lns)
        job_est_d = sum(float(ln.get("extra_st_deducted") or 0) for ln in job_lns)
        job_it_a = sum(float(ln.get("it_amount") or 0) for ln in job_lns)
        job_oth_a = sum(float(ln.get("other_amount") or 0) for ln in job_lns)
        
        # Add cheque-level deductions proportionally to first job or distribute as needed
        # For simplicity, we add cheque-level deductions to the first job's receipt
        if pid == list(job_lines.keys())[0]:
            job_it_a += it_deducted
            job_oth_a += other_adjustable
            job_st_d += st_deducted
            job_st_r += st_received
            job_est_d += extra_st_deduction
        
        # Calculate amount received for this job
        # Formula: Amount Received = Cheque Share + Adjustable - Non-Adjustable (ST Received)
        received = job_cheque_share + job_it_a + job_oth_a - job_st_r
        
        cheque_row = query("SELECT * FROM cheques WHERE id=?", (cheque_id,), one=True) if cheque_id else None
        receipt_txn_id = execute("""INSERT INTO transactions
            (project_id,txn_month,txn_year,txn_type,amount,
             cheque_no,cheque_date,cheque_amount,
             it_adjustable,pra_adjustable,other_adjustable,
             st_received,st_deducted,extra_st_deducted,amount_received,
             description)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (pid, month, year, "RECEIPT", received,
             cheque_row["cheque_no"] if cheque_row else "",
             cheque_row["cheque_date"] if cheque_row else None,
             job_cheque_share,
             job_it_a, pra_fee if pid == list(job_lines.keys())[0] else 0, job_oth_a,
             job_st_r, job_st_d, job_est_d, received,
             f"Auto-booked via Performa {perf_no}"))
        
        rebuild_snapshot(pid, month, year)

    # Insert performa_lines for each invoice (detail layer)
    for l in lines:
        pid = int(l["project_id"])
        inv_txn_id = l.get("invoice_txn_id")
        cheque_share = float(l.get("cheque_share") or 0)
        st_r  = float(l.get("st_received") or 0)
        st_d  = float(l.get("st_deducted") or 0)
        est_d = float(l.get("extra_st_deducted") or 0)
        it_a  = float(l.get("it_amount") or 0)
        oth_a = float(l.get("other_amount") or 0)
        pst_rate = float(l.get("pst_rate") or 0)
        pst_amt  = float(l.get("pst_amount") or 0)

        execute("""INSERT INTO performa_lines
            (performa_id, project_id, invoice_txn_id, invoice_no, invoice_date,
             invoice_amount, invoice_tax, invoice_gross,
             pst_rate, pst_amount, it_amount, other_amount, cheque_share,
             st_received, st_deducted, extra_st_deducted,
             client_name, client_ntn, remarks,
             t2_invoice_amt, t2_it_formula, t2_pra_formula, t2_oadj_formula,
             t2_sded_formula, t2_srcv_formula, t2_estd_formula, t2_oded_formula, t2_remarks)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (perf_id, pid, inv_txn_id, l.get("invoice_no"), l.get("invoice_date"),
             float(l.get("invoice_amount") or 0), float(l.get("invoice_tax") or 0), float(l.get("invoice_gross") or 0),
             pst_rate, pst_amt, it_a, oth_a, cheque_share,
             st_r, st_d, est_d,
             l.get("client_name"), l.get("client_ntn"), l.get("remarks"),
             float(l.get("t2_invoice_amt") or 0), l.get("t2_it_formula"), l.get("t2_pra_formula"), l.get("t2_oadj_formula"),
             l.get("t2_sded_formula"), l.get("t2_srcv_formula"), l.get("t2_estd_formula"), l.get("t2_oded_formula"), l.get("t2_remarks")))

    return jsonify({"ok": True, "id": perf_id, "performa_no": perf_no})

@app.route("/api/performa/<int:perf_id>", methods=["DELETE"])
@login_required
def api_performa_delete(perf_id):
    """Delete a performa AND its auto-created receipt transactions."""
    if session.get("role") != "admin":
        return jsonify({"error":"Admin only"}), 403
    lines = query("SELECT * FROM performa_lines WHERE performa_id=?", (perf_id,))
    receipt_ids_to_clean = []
    for l in lines:
        if l["receipt_txn_id"]:
            txn = query("SELECT * FROM transactions WHERE id=?", (l["receipt_txn_id"],), one=True)
            if txn:
                receipt_ids_to_clean.append((l["receipt_txn_id"], txn["project_id"], txn["txn_month"], txn["txn_year"]))
    # delete performa (cascades to performa_lines via FK ON DELETE CASCADE)
    execute("DELETE FROM performas WHERE id=?", (perf_id,))
    # now safe to delete the orphaned receipt transactions
    for tid, pid, m, y in receipt_ids_to_clean:
        execute("DELETE FROM transactions WHERE id=?", (tid,))
        rebuild_snapshot(pid, m, y)
    return jsonify({"ok": True})

# ── API: REPORTS ──────────────────────────────────────────────────────────────
@app.route("/api/reports/summary")
@login_required
def api_report_summary():
    month = int(request.args.get("month", date.today().month))
    year  = int(request.args.get("year",  date.today().year))
    pm    = request.args.get("pm","")
    grp   = request.args.get("group","")
    sql = """
        SELECT p.*,
            COALESCE(s.billing_upto,0) billing_upto,
            COALESCE(s.receipt_upto,0) receipt_upto,
            COALESCE(s.salary_upto,0)  salary_upto,
            COALESCE(s.direct_upto,0)  direct_upto,
            COALESCE(s.receivable,0)   receivable,
            COALESCE(s.profit_loss_billing,0)  pl_billing,
            COALESCE(s.profit_loss_receipt,0)  pl_receipt
        FROM projects p
        LEFT JOIN monthly_snapshot s ON s.project_id=p.id AND s.snap_year=? AND s.snap_month=?
        WHERE p.is_active=1
    """
    params=[year,month]
    if pm:  sql+=" AND p.project_manager=?"; params.append(pm)
    if grp: sql+=" AND p.project_group=?";   params.append(grp)
    sql+=" ORDER BY p.project_manager,p.sheet_ref"
    rows = query(sql,params)
    return jsonify([dict(r) for r in rows])

@app.route("/api/reports/pm")
@login_required
def api_report_pm():
    month = int(request.args.get("month", date.today().month))
    year  = int(request.args.get("year",  date.today().year))
    rows = query("""
        SELECT p.project_manager,
            COUNT(*) cnt,
            SUM(COALESCE(s.billing_upto,0)) billing,
            SUM(COALESCE(s.receipt_upto,0)) receipt,
            SUM(COALESCE(s.receivable,0))   receivable,
            SUM(COALESCE(s.profit_loss_billing,0)) pl
        FROM projects p
        LEFT JOIN monthly_snapshot s ON s.project_id=p.id AND s.snap_year=? AND s.snap_month=?
        WHERE p.is_active=1
        GROUP BY p.project_manager
        ORDER BY billing DESC
    """, (year,month))
    return jsonify([dict(r) for r in rows])

@app.route("/api/reports/history")
@login_required
def api_report_history():
    fm = int(request.args.get("from_month",7))
    fy = int(request.args.get("from_year",2024))
    tm = int(request.args.get("to_month", date.today().month))
    ty = int(request.args.get("to_year",  date.today().year))
    pm = request.args.get("pm","")
    typ= request.args.get("type","")
    sql = """SELECT t.*,p.sheet_ref,p.job_no,p.project_name,p.project_manager
             FROM transactions t JOIN projects p ON p.id=t.project_id
             WHERE (t.txn_year>? OR (t.txn_year=? AND t.txn_month>=?))
               AND (t.txn_year<? OR (t.txn_year=? AND t.txn_month<=?))"""
    params=[fy,fy,fm,ty,ty,tm]
    if pm:  sql+=" AND p.project_manager=?"; params.append(pm)
    if typ: sql+=" AND t.txn_type=?";        params.append(typ)
    sql+=" ORDER BY t.txn_year,t.txn_month,p.sheet_ref"
    rows = query(sql,params)
    return jsonify([dict(r) for r in rows])

# ── API: META ─────────────────────────────────────────────────────────────────
def get_pm_list():
    master = query("SELECT full_name FROM pm_master WHERE is_active=1 ORDER BY full_name")
    if master:
        return [r["full_name"] for r in master]
    row = query("SELECT value FROM settings WHERE key='PM_LIST'", one=True)
    if row and row["value"]:
        lst = [x.strip() for x in row["value"].split("||") if x.strip()]
        if lst: return lst
    return PROJECT_MANAGERS

def get_group_list():
    row = query("SELECT value FROM settings WHERE key='GROUP_LIST'", one=True)
    if row and row["value"]:
        lst = [x.strip() for x in row["value"].split("||") if x.strip()]
        if lst: return lst
    return PROJECT_GROUPS

@app.route("/api/meta")
@login_required
def api_meta():
    return jsonify({
        "project_managers": get_pm_list(),
        "project_groups":   get_group_list(),
        "tax_rates":        TAX_RATES,
        "invoice_prefix":   INVOICE_PREFIX,
        "role":             session.get("role","guest"),
        "available_fys":    get_available_fys(),
        "current_fy_start": get_current_fy()[0],
    })

@app.route("/api/projects/list")
@login_required
def api_project_list():
    rows = query("SELECT id,sheet_ref,job_no,project_name,project_manager,project_group,nespak_fee_mil from projects WHERE is_active=1 ORDER BY project_manager,sheet_ref")
    return jsonify([dict(r) for r in rows])

# ── API: EXPORT ───────────────────────────────────────────────────────────────
@app.route("/api/export/list")
@login_required
def api_export_list():
    """Export any of the 5 list views (Invoices/Receipts/Expenses/Cheques/Performa)
    to Excel, using the exact same period+filters as the on-screen view."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment
        from openpyxl.utils import get_column_letter
    except ImportError:
        return jsonify({"error":"openpyxl not installed"}), 500

    entity = request.args.get("entity")
    args = {
        "fy_start": request.args.get("fy_start", ""),
        "month":    request.args.get("month", ""),
        "year":     request.args.get("year", ""),
        "cumulative": request.args.get("cumulative", "1"),
        "pm":     request.args.get("pm", ""),
        "group":  request.args.get("group", ""),
        "client": request.args.get("client", ""),
        "job":    request.args.get("job", ""),
    }
    data = compute_period_list(entity, args)
    if "error" in data:
        return jsonify(data), 400
    rows = data["rows"]
    totals = data["totals"]
    period_label = data["period_label"]

    col_defs = {
        "invoices": [
            ("sheet_ref","Ref"),("job_no","Job No."),("project_name","Project"),
            ("project_manager","PM"),("client_name","Client"),
            (None,"Period"),("invoice_no","Invoice No."),("invoice_date","Inv. Date"),
            ("amount","Amount"),("tax_amount","GST"),("gross_amount","Gross"),
            (None,"Attached"),("description","Note"),
        ],
        "receipts": [
            ("sheet_ref","Ref"),("job_no","Job No."),("project_name","Project"),
            ("project_manager","PM"),("client_name","Client"),
            (None,"Period"),("cheque_no","Cheque No."),("cheque_date","Chq Date"),
            ("cheque_amount","Chq Amount"),("it_adjustable","IT"),("pra_adjustable","PRA"),
            ("other_adjustable","Other Adj."),("st_received","ST Received"),
            ("st_deducted","ST Deducted"),("extra_st_deducted","Extra ST Ded."),
            ("amount_received","Amt Received"),(None,"Attached"),("description","Note"),
        ],
        "expenses": [
            ("sheet_ref","Ref"),("job_no","Job No."),("project_name","Project"),
            ("project_manager","PM"),(None,"Period"),
            ("salary_actual","Salary"),("direct_actual","Direct"),(None,"Total"),
            ("description","Note"),
        ],
        "cheques": [
            ("id","Sr."),("cheque_no","Cheque No."),("cheque_date","Date"),
            (None,"Period"),("amount","Amount"),("allocated","Allocated"),
            ("remaining","Remaining"),(None,"Status"),("remarks","Remarks"),
        ],
        "performa": [
            ("performa_no","Performa No."),("cheque_no","Cheque No."),
            ("cheque_date","Cheque Date"),(None,"Period"),
            ("total_amount","Total Amount"),("created_at","Created"),
        ],
    }
    if entity not in col_defs:
        return jsonify({"error":"Unknown entity"}), 400
    cols = col_defs[entity]

    wb = Workbook()
    ws = wb.active
    ws.title = entity.capitalize()[:30]

    ws.merge_cells(f"A1:{get_column_letter(len(cols))}1")
    ws["A1"] = f"NESPAK — Construction Management Division — {entity.capitalize()}"
    ws["A1"].font = Font(bold=True, size=13, color="1565C0")
    ws["A1"].alignment = Alignment(horizontal="center")
    ws.merge_cells(f"A2:{get_column_letter(len(cols))}2")
    ws["A2"] = f"Period: {period_label}"
    ws["A2"].font = Font(bold=True, size=10, color="1976D2")
    ws["A2"].alignment = Alignment(horizontal="center")

    hdr_fill = PatternFill("solid", fgColor="1565C0")
    for c, (key, label) in enumerate(cols, 1):
        cell = ws.cell(row=4, column=c, value=label)
        cell.font = Font(bold=True, color="FFFFFF", size=9)
        cell.fill = hdr_fill
        cell.alignment = Alignment(horizontal="center")
        ws.column_dimensions[get_column_letter(c)].width = 16

    MONTHS_S_PY = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    row_n = 5
    for r in rows:
        for c, (key, label) in enumerate(cols, 1):
            if key is None:
                if label == "Period":
                    v = f"{MONTHS_S_PY[r['txn_month']-1]}-{r['txn_year']}" if r.get("txn_month") else ""
                elif label == "Attached":
                    v = "Yes" if r.get("attachment_name") else "No"
                elif label == "Status":
                    v = "Fully Booked" if (r.get("remaining") or 0) <= 0.5 else "Open"
                elif label == "Total":
                    v = (r.get("salary_actual") or 0) + (r.get("direct_actual") or 0)
                else:
                    v = ""
            else:
                v = r.get(key, "")
            cell = ws.cell(row=row_n, column=c, value=v)
            cell.font = Font(size=9)
            if isinstance(v, (int, float)) and key not in ("id",):
                cell.number_format = '#,##0.00'
                cell.alignment = Alignment(horizontal="right")
        row_n += 1

    # totals row
    row_n += 1
    ws.cell(row=row_n, column=1, value="TOTAL").font = Font(bold=True, color="1565C0")
    for k, v in totals.items():
        if k == "count": continue
    ws.freeze_panes = "A5"

    os.makedirs(EXPORT_FOLDER, exist_ok=True)
    fname = f"NESPAK_{entity}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    path = os.path.join(EXPORT_FOLDER, fname)
    wb.save(path)
    return send_file(os.path.abspath(path), as_attachment=True, download_name=fname)

@app.route("/api/export")
@login_required
def api_export():
    try: import openpyxl
    except: return jsonify({"error":"openpyxl not installed. Run: pip install openpyxl"}),500

    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter

    args = {
        "pm": request.args.get("pm",""),
        "group": request.args.get("group",""),
        "client": request.args.get("client",""),
        "active": request.args.get("active","all"),
        "fy_start": request.args.get("fy_start",""),
        "month": request.args.get("month",""),
        "year": request.args.get("year",""),
        "cumulative": request.args.get("cumulative","1"),
    }
    data = compute_projects_summary(args)
    rows = data["projects"]
    period_label = data["period_label"]

    wb = Workbook()
    if "Sheet" in wb.sheetnames: del wb["Sheet"]

    def hdr(cell, txt, bg="1565C0"):
        cell.value=txt
        cell.font=Font(name="Calibri",bold=True,color="FFFFFF",size=9)
        cell.fill=PatternFill("solid",fgColor=bg)
        cell.alignment=Alignment(horizontal="center",vertical="center",wrap_text=True)

    def num(cell, v):
        cell.value=v; cell.number_format='#,##0.00'
        cell.alignment=Alignment(horizontal="right")
        cell.font=Font(name="Calibri",size=9,
                       color="DC2626" if isinstance(v,(int,float)) and v<0 else "000000")

    ws = wb.create_sheet("Summary")
    ws.merge_cells("A1:P1")
    ws["A1"]=f"NESPAK — CONSTRUCTION MANAGEMENT DIVISION"
    ws["A1"].font=Font(name="Calibri",bold=True,size=13,color="1565C0")
    ws["A1"].alignment=Alignment(horizontal="center")
    ws.merge_cells("A2:P2")
    ws["A2"]=f"DIVISIONAL MONITORING OF PROJECTS — {period_label}"
    ws["A2"].font=Font(name="Calibri",bold=True,size=10,color="1976D2")
    ws["A2"].alignment=Alignment(horizontal="center")

    # Columns match EXACTLY what the Projects screen shows (period figures, incl. P/L Billing)
    hdrs=["S.No","Ref","Job No.","Project Name","PM","Client","Group","Fee(M)",
          "Billing(Rs.)","Last Bill","Receipt(Rs.)","Last Rcpt","Receivable",
          "Salary","Direct","P/L Billing"]
    ws_=[5,8,9,32,18,14,9,8,14,10,14,10,13,12,12,13]
    for c,(h,w) in enumerate(zip(hdrs,ws_),1):
        hdr(ws.cell(4,c),h)
        ws.column_dimensions[get_column_letter(c)].width=w
    ws.row_dimensions[4].height=32

    from itertools import groupby
    rows_s=sorted(rows,key=lambda r: r["project_manager"] or "")
    rn=5; sno=1
    num_cols = [9,11,13,14,15,16]  # Billing, Receipt, Receivable, Salary, Direct, P/L
    grand=[0.0]*6

    for pm_name,pm_rows in groupby(rows_s,key=lambda r:r["project_manager"]):
        pm_rows=list(pm_rows)
        ws.merge_cells(f"A{rn}:P{rn}")
        c=ws.cell(rn,1,f"  PM:  {pm_name}")
        c.font=Font(name="Calibri",bold=True,color="FFFFFF",size=9)
        c.fill=PatternFill("solid",fgColor="1976D2")
        rn+=1
        pm_tot=[0.0]*6
        for i,r in enumerate(pm_rows):
            bg="FFFFFF" if i%2==0 else "EFF6FF"
            fl=PatternFill("solid",fgColor=bg)
            vals=[sno,r["sheet_ref"],r["job_no"],r["project_name"],
                  r["project_manager"],r.get("client_name") or "—",r["project_group"],r["nespak_fee_mil"],
                  r["period_billing"],r.get("last_billing") or "—",
                  r["period_receipt"],r.get("last_receipt") or "—",
                  r["period_receivable"],r["period_salary"],r["period_direct"],r["period_pl_billing"]]
            for c2,v in enumerate(vals,1):
                cell=ws.cell(rn,c2,v); cell.fill=fl
                cell.font=Font(name="Calibri",size=9)
                if c2 in num_cols: num(cell,float(v or 0))
                else: cell.alignment=Alignment(horizontal="left")
            for j,col in enumerate(num_cols):
                pm_tot[j]+=float(vals[col-1] or 0)
            sno+=1; rn+=1
        ws.cell(rn,4,"Sub-Total").font=Font(bold=True,size=9,color="1565C0")
        for j,col in enumerate(num_cols):
            cell=ws.cell(rn,col); cell.fill=PatternFill("solid",fgColor="DBEAFE")
            num(cell,pm_tot[j]); cell.font=Font(name="Calibri",bold=True,size=9,color="1565C0")
            grand[j]+=pm_tot[j]
        rn+=1
    rn+=1
    ws.cell(rn,4,"GRAND TOTAL").font=Font(bold=True,color="FFFFFF",size=10)
    for c in range(1,17): ws.cell(rn,c).fill=PatternFill("solid",fgColor="1565C0")
    for j,col in enumerate(num_cols):
        cell=ws.cell(rn,col); num(cell,grand[j])
        cell.font=Font(name="Calibri",bold=True,color="FFFFFF",size=10)
    ws.freeze_panes="A5"

    os.makedirs(EXPORT_FOLDER, exist_ok=True)
    fname=f"NESPAK_CMD_Summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    path=os.path.join(EXPORT_FOLDER,fname)
    wb.save(path)
    return send_file(os.path.abspath(path), as_attachment=True, download_name=fname)

# ── API: SETTINGS ─────────────────────────────────────────────────────────────
@app.route("/api/settings", methods=["GET","POST"])
@login_required
def api_settings():
    if request.method=="POST":
        if session.get("role")!="admin":
            return jsonify({"error":"Admin only"}),403
        d=request.get_json()
        for k,v in d.items():
            execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(k,v))
        return jsonify({"ok":True})
    rows=query("SELECT * FROM settings")
    return jsonify({r["key"]:r["value"] for r in rows})

if __name__ == "__main__":
    init_db()
    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print("\n" + "="*60)
    print("NESPAK Project Monitoring System")
    print("="*60)
    print(f"Local:   http://localhost:5000")
    print(f"Network: http://{local_ip}:5000")
    print("\nAdmin password: admin123")
    print("Guest password: guest123")
    print("\nPress Ctrl+C to stop the server.")
    print("="*60 + "\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
