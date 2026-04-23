import os
from datetime import datetime, date, timedelta
from decimal import Decimal
from functools import wraps

import psycopg2
from psycopg2.extras import RealDictCursor
import pymysql
from pymysql.cursors import DictCursor
import requests

from flask import Flask, render_template, request, redirect, url_for, flash, session, abort, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "wasco-dev-secret-key")

# PostgreSQL - Supabase primary database
PG_HOST = os.getenv("PG_HOST", "aws-0-eu-west-1.pooler.supabase.com")
PG_PORT = int(os.getenv("PG_PORT") or 5432)
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASSWORD = os.getenv("PG_PASSWORD", "")
PG_DATABASE = os.getenv("PG_DATABASE", "postgres")

# MySQL - Railway secondary database
MYSQL_HOST = os.getenv("MYSQL_HOST", "mysql.railway.internal")
MYSQL_PORT = int(os.getenv("MYSQL_PORT") or 3306)
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "railway")

PAYMENT_GATEWAY_MODE = os.getenv("PAYMENT_GATEWAY_MODE", "mock")
PAYMENT_PROVIDER_NAME = os.getenv("PAYMENT_PROVIDER_NAME", "Online Payment Gateway")
PAYMENT_CALLBACK_BASE = os.getenv("PAYMENT_CALLBACK_BASE", "http://127.0.0.1:5000")

# Sendbird configuration
SENDBIRD_APP_ID = os.getenv("SENDBIRD_APP_ID", "F2312217-DBA2-4180-8B7D-324DF3F54DCB")
SENDBIRD_API_TOKEN = os.getenv("SENDBIRD_API_TOKEN", "")
SENDBIRD_BASE_URL = f"https://api-{SENDBIRD_APP_ID}.sendbird.com/v3"
WASCO_SUPPORT_USER_ID = os.getenv("WASCO_SUPPORT_USER_ID", "wasco_support")
WASCO_SUPPORT_NICKNAME = os.getenv("WASCO_SUPPORT_NICKNAME", "WASCO Support")


# --------------------------
# Database helpers
# --------------------------
def get_pg_connection():
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        user=PG_USER,
        password=PG_PASSWORD,
        dbname=PG_DATABASE,
        sslmode="require",
        cursor_factory=RealDictCursor,
    )


def get_mysql_connection():
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        cursorclass=DictCursor,
        autocommit=False,
        connect_timeout=15,
        read_timeout=15,
        write_timeout=15,
        charset="utf8mb4",
    )


def fetch_all_pg(sql, params=None):
    conn = get_pg_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return list(cur.fetchall())
    finally:
        conn.close()


def fetch_one_pg(sql, params=None):
    conn = get_pg_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchone()
    finally:
        conn.close()


def execute_pg(sql, params=None, fetch=False):
    conn = get_pg_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            result = cur.fetchone() if fetch else None
        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def fetch_all_mysql(sql, params=None):
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return list(cur.fetchall())
    finally:
        conn.close()


def fetch_one_mysql(sql, params=None):
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchone()
    finally:
        conn.close()


def execute_mysql(sql, params=None, fetch=False):
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            result = cur.fetchone() if fetch else None
        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def mysql_available():
    try:
        print("MYSQL CONFIG:", MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_DATABASE)
        conn = get_mysql_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT 1 AS ok")
            cur.fetchone()
        conn.close()
        return True
    except Exception as e:
        print("MYSQL CONNECTION ERROR:", e)
        return False


def scalar_pg(sql, params=None):
    row = fetch_one_pg(sql, params)
    if not row:
        return None
    return next(iter(row.values()))


def scalar_mysql(sql, params=None):
    row = fetch_one_mysql(sql, params)
    if not row:
        return None
    return next(iter(row.values()))


def safe_decimal(value):
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


# --------------------------
# Auth / session helpers
# --------------------------
def current_user():
    return session.get("user")


@app.context_processor
def inject_globals():
    return {
        "current_user": current_user(),
        "year": datetime.now().year,
        "payment_provider_name": PAYMENT_PROVIDER_NAME,
    }


def login_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user:
                flash("Please sign in to continue.", "warning")
                return redirect(url_for("login", next=request.path))
            if roles and user.get("role") not in roles:
                abort(403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def verify_password(stored_hash, password):
    if not stored_hash:
        return False
    stored_hash = str(stored_hash)
    if stored_hash.startswith(("pbkdf2:", "scrypt:")):
        return check_password_hash(stored_hash, password)
    return stored_hash == password


def log_action(user_id, action_name, details):
    try:
        execute_pg(
            """
            INSERT INTO audit_logs (user_id, action_name, action_details)
            VALUES (%s, %s, %s)
            """,
            (user_id, action_name, details),
        )
    except Exception as e:
        print("AUDIT LOG ERROR:", e)


# --------------------------
# Payment gateway placeholder
# --------------------------
class PaymentGateway:
    def __init__(self, mode="mock", provider="Online Payment Gateway"):
        self.mode = mode
        self.provider = provider

    def initiate(self, bill, user):
        ref = f"WASCO-{bill['bill_id']}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        log_action(user["user_id"], "online_payment_initiated", f"Bill {bill['bill_id']} / ref {ref}")
        return {
            "checkout_reference": ref,
            "provider": self.provider,
            "mode": self.mode,
            "callback_url": f"{PAYMENT_CALLBACK_BASE}/payments/callback?reference={ref}&status=initiated",
        }


payment_gateway = PaymentGateway(PAYMENT_GATEWAY_MODE, PAYMENT_PROVIDER_NAME)


# --------------------------
# Sendbird helpers
# --------------------------
def sendbird_headers():
    return {
        "Api-Token": SENDBIRD_API_TOKEN,
        "Content-Type": "application/json",
    }


def sendbird_enabled():
    return bool(SENDBIRD_API_TOKEN and SENDBIRD_APP_ID)


def sendbird_request(method, path, payload=None, params=None):
    url = f"{SENDBIRD_BASE_URL}{path}"
    response = requests.request(
        method=method,
        url=url,
        headers=sendbird_headers(),
        json=payload,
        params=params,
        timeout=20,
    )
    if response.status_code >= 400:
        raise Exception(f"Sendbird error {response.status_code}: {response.text}")
    if response.text:
        return response.json()
    return {}


def get_sendbird_customer_user_id(customer):
    return f"customer_{customer['customer_id']}"


def ensure_sendbird_user(user_id, nickname):
    payload = {
        "user_id": user_id,
        "nickname": nickname,
        "issue_access_token": False,
    }
    try:
        return sendbird_request("POST", "/users", payload=payload)
    except Exception as e:
        message = str(e).lower()
        if "already exists" in message or "400202" in message:
            return sendbird_request("GET", f"/users/{user_id}")
        raise


def ensure_support_user():
    return ensure_sendbird_user(WASCO_SUPPORT_USER_ID, WASCO_SUPPORT_NICKNAME)


def get_or_create_support_channel(customer):
    customer_user_id = get_sendbird_customer_user_id(customer)
    customer_name = f"{customer['first_name']} {customer['last_name']}".strip()

    ensure_support_user()
    ensure_sendbird_user(customer_user_id, customer_name)

    payload = {
        "user_ids": [customer_user_id, WASCO_SUPPORT_USER_ID],
        "is_distinct": True,
        "name": f"WASCO Support - {customer_name}",
        "custom_type": "customer_support",
        "data": str({
            "customer_id": customer["customer_id"],
            "account_number": customer["account_number"],
            "district": customer["district"],
        }),
    }
    return sendbird_request("POST", "/group_channels", payload=payload)


def list_channel_messages(channel_url):
    now_ts = int(datetime.now().timestamp() * 1000)
    return sendbird_request(
        "GET",
        f"/group_channels/{channel_url}/messages",
        params={
            "message_ts": now_ts,
            "prev_limit": 50,
            "next_limit": 0,
            "include": True,
        },
    )


def send_user_message(channel_url, user_id, message):
    payload = {
        "message_type": "MESG",
        "user_id": user_id,
        "message": message,
    }
    return sendbird_request("POST", f"/group_channels/{channel_url}/messages", payload=payload)


# --------------------------
# Secondary database sync helpers
# --------------------------

def sync_branch_to_secondary(branch_id):
    try:
        if not mysql_available():
            print("MYSQL NOT AVAILABLE: sync_branch_to_secondary")
            return

        branch = fetch_one_pg(
            """
            SELECT branch_id, branch_name, district, branch_manager_name, phone, email, created_at
            FROM branches
            WHERE branch_id = %s
            """,
            (branch_id,),
        )
        if not branch:
            print("BRANCH NOT FOUND IN POSTGRES:", branch_id)
            return

        existing = fetch_one_mysql(
            "SELECT branch_id FROM branches WHERE branch_id = %s",
            (branch["branch_id"],),
        )

        if existing:
            execute_mysql(
                """
                UPDATE branches
                SET branch_name=%s, district=%s, branch_manager_name=%s, phone=%s, email=%s, created_at=%s
                WHERE branch_id=%s
                """,
                (
                    branch["branch_name"],
                    branch["district"],
                    branch["branch_manager_name"],
                    branch["phone"],
                    branch["email"],
                    branch["created_at"],
                    branch["branch_id"],
                ),
            )
        else:
            execute_mysql(
                """
                INSERT INTO branches
                (branch_id, branch_name, district, branch_manager_name, phone, email, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    branch["branch_id"],
                    branch["branch_name"],
                    branch["district"],
                    branch["branch_manager_name"],
                    branch["phone"],
                    branch["email"],
                    branch["created_at"],
                ),
            )

        print("MYSQL SYNC OK: branches", branch_id)
    except Exception as e:
        print("MYSQL SYNC ERROR in sync_branch_to_secondary:", e)


def sync_rate_to_secondary(rate_id):
    try:
        if not mysql_available():
            print("MYSQL NOT AVAILABLE: sync_rate_to_secondary")
            return

        rate = fetch_one_pg(
            """
            SELECT rate_id, rate_tier, min_units, max_units, price_per_unit,
                   fixed_charge, effective_from, active_status
            FROM billing_rates
            WHERE rate_id = %s
            """,
            (rate_id,),
        )
        if not rate:
            print("RATE NOT FOUND IN POSTGRES:", rate_id)
            return

        existing = fetch_one_mysql("SELECT rate_id FROM billing_rates WHERE rate_tier = %s", (rate["rate_tier"],))
        if existing:
            execute_mysql(
                """
                UPDATE billing_rates
                SET min_units=%s, max_units=%s, price_per_unit=%s,
                    fixed_charge=%s, effective_from=%s, active_status=%s
                WHERE rate_tier=%s
                """,
                (
                    rate["min_units"],
                    rate["max_units"],
                    rate["price_per_unit"],
                    rate["fixed_charge"],
                    rate["effective_from"],
                    rate["active_status"],
                    rate["rate_tier"],
                ),
            )
        else:
            execute_mysql(
                """
                INSERT INTO billing_rates
                (rate_id, rate_tier, min_units, max_units, price_per_unit, fixed_charge, effective_from, active_status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    rate["rate_id"],
                    rate["rate_tier"],
                    rate["min_units"],
                    rate["max_units"],
                    rate["price_per_unit"],
                    rate["fixed_charge"],
                    rate["effective_from"],
                    rate["active_status"],
                ),
            )
        print("MYSQL SYNC OK: billing_rates", rate_id)
    except Exception as e:
        print("MYSQL SYNC ERROR in sync_rate_to_secondary:", e)


def sync_user_to_secondary(user_id):
    try:
        if not mysql_available():
            print("MYSQL NOT AVAILABLE: sync_user_to_secondary")
            return

        user = fetch_one_pg(
            """
            SELECT user_id, full_name, email, password_hash, role, branch_id, is_active, created_at
            FROM users
            WHERE user_id = %s
            """,
            (user_id,),
        )
        if not user:
            print("USER NOT FOUND IN POSTGRES:", user_id)
            return

        if user["branch_id"] is not None:
            sync_branch_to_secondary(user["branch_id"])

        existing = fetch_one_mysql("SELECT user_id FROM users WHERE email = %s", (user["email"],))
        if existing:
            execute_mysql(
                """
                UPDATE users
                SET full_name=%s, password_hash=%s, role=%s, branch_id=%s, is_active=%s
                WHERE email=%s
                """,
                (
                    user["full_name"],
                    user["password_hash"],
                    user["role"],
                    user["branch_id"],
                    user["is_active"],
                    user["email"],
                ),
            )
        else:
            execute_mysql(
                """
                INSERT INTO users
                (user_id, full_name, email, password_hash, role, branch_id, is_active, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    user["user_id"],
                    user["full_name"],
                    user["email"],
                    user["password_hash"],
                    user["role"],
                    user["branch_id"],
                    user["is_active"],
                    user.get("created_at"),
                ),
            )
        print("MYSQL SYNC OK: users", user_id)
    except Exception as e:
        print("MYSQL SYNC ERROR in sync_user_to_secondary:", e)

def sync_customer_to_secondary(customer_id):
    try:
        if not mysql_available():
            print("MYSQL NOT AVAILABLE: sync_customer_to_secondary")
            return

        customer = fetch_one_pg(
            """
            SELECT c.customer_id, c.user_id, c.branch_id, c.account_number, c.meter_number,
                   c.first_name, c.last_name, c.email, c.phone, c.district, c.address,
                   c.customer_type, c.created_at, u.email AS user_email
            FROM customers c
            LEFT JOIN users u ON u.user_id = c.user_id
            WHERE c.customer_id = %s
            """,
            (customer_id,),
        )
        if not customer:
            print("CUSTOMER NOT FOUND IN POSTGRES:", customer_id)
            return

        if customer["branch_id"] is not None:
            sync_branch_to_secondary(customer["branch_id"])

        secondary_user_id = None
        if customer["user_id"]:
            sync_user_to_secondary(customer["user_id"])
            row = fetch_one_mysql("SELECT user_id FROM users WHERE email = %s", (customer["user_email"],))
            secondary_user_id = row["user_id"] if row else None

        existing = fetch_one_mysql("SELECT customer_id FROM customers WHERE account_number = %s", (customer["account_number"],))
        if existing:
            execute_mysql(
                """
                UPDATE customers
                SET user_id=%s, branch_id=%s, meter_number=%s, first_name=%s, last_name=%s,
                    email=%s, phone=%s, district=%s, address=%s, customer_type=%s
                WHERE account_number=%s
                """,
                (
                    secondary_user_id,
                    customer["branch_id"],
                    customer["meter_number"],
                    customer["first_name"],
                    customer["last_name"],
                    customer["email"],
                    customer["phone"],
                    customer["district"],
                    customer["address"],
                    customer["customer_type"],
                    customer["account_number"],
                ),
            )
        else:
            execute_mysql(
                """
                INSERT INTO customers
                (customer_id, user_id, branch_id, account_number, meter_number, first_name, last_name, email, phone, district, address, customer_type, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    customer["customer_id"],
                    secondary_user_id,
                    customer["branch_id"],
                    customer["account_number"],
                    customer["meter_number"],
                    customer["first_name"],
                    customer["last_name"],
                    customer["email"],
                    customer["phone"],
                    customer["district"],
                    customer["address"],
                    customer["customer_type"],
                    customer.get("created_at"),
                ),
            )
        print("MYSQL SYNC OK: customers", customer_id)
    except Exception as e:
        print("MYSQL SYNC ERROR in sync_customer_to_secondary:", e)

def sync_usage_to_secondary(usage_id):
    try:
        if not mysql_available():
            print("MYSQL NOT AVAILABLE: sync_usage_to_secondary")
            return

        usage = fetch_one_pg(
            """
            SELECT w.usage_id, w.usage_month, w.previous_reading, w.current_reading, w.units_used,
                   c.account_number
            FROM water_usage w
            JOIN customers c ON c.customer_id = w.customer_id
            WHERE w.usage_id = %s
            """,
            (usage_id,),
        )
        if not usage:
            print("USAGE NOT FOUND IN POSTGRES:", usage_id)
            return

        secondary_customer = fetch_one_mysql(
            "SELECT customer_id FROM customers WHERE account_number = %s",
            (usage["account_number"],)
        )
        if not secondary_customer:
            print("MYSQL CUSTOMER NOT FOUND FOR USAGE:", usage["account_number"])
            return

        existing = fetch_one_mysql("SELECT usage_id FROM water_usage WHERE usage_id = %s", (usage["usage_id"],))
        if existing:
            execute_mysql(
                """
                UPDATE water_usage
                SET customer_id=%s, usage_month=%s, previous_reading=%s, current_reading=%s, units_used=%s
                WHERE usage_id=%s
                """,
                (
                    secondary_customer["customer_id"],
                    usage["usage_month"],
                    usage["previous_reading"],
                    usage["current_reading"],
                    usage["units_used"],
                    usage["usage_id"],
                ),
            )
        else:
            execute_mysql(
                """
                INSERT INTO water_usage
                (usage_id, customer_id, usage_month, previous_reading, current_reading, units_used)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    usage["usage_id"],
                    secondary_customer["customer_id"],
                    usage["usage_month"],
                    usage["previous_reading"],
                    usage["current_reading"],
                    usage["units_used"],
                ),
            )
        print("MYSQL SYNC OK: water_usage", usage_id)
    except Exception as e:
        print("MYSQL SYNC ERROR in sync_usage_to_secondary:", e)


def sync_bill_to_secondary(bill_id):
    try:
        if not mysql_available():
            print("MYSQL NOT AVAILABLE: sync_bill_to_secondary")
            return

        bill = fetch_one_pg(
            """
            SELECT b.bill_id, b.bill_month, b.units_used, b.amount_due, b.outstanding_amount,
                   b.status, b.due_date, c.account_number, w.usage_id, r.rate_id
            FROM bills b
            JOIN customers c ON c.customer_id = b.customer_id
            LEFT JOIN water_usage w ON w.usage_id = b.usage_id
            LEFT JOIN billing_rates r ON r.rate_id = b.rate_id
            WHERE b.bill_id = %s
            """,
            (bill_id,),
        )
        if not bill:
            print("BILL NOT FOUND IN POSTGRES:", bill_id)
            return

        secondary_customer = fetch_one_mysql(
            "SELECT customer_id FROM customers WHERE account_number = %s",
            (bill["account_number"],)
        )
        if not secondary_customer:
            print("MYSQL CUSTOMER NOT FOUND FOR BILL:", bill["account_number"])
            return

        existing = fetch_one_mysql("SELECT bill_id FROM bills WHERE bill_id = %s", (bill["bill_id"],))
        if existing:
            execute_mysql(
                """
                UPDATE bills
                SET customer_id=%s, usage_id=%s, rate_id=%s, bill_month=%s, units_used=%s,
                    amount_due=%s, outstanding_amount=%s, status=%s, due_date=%s
                WHERE bill_id=%s
                """,
                (
                    secondary_customer["customer_id"],
                    bill["usage_id"],
                    bill["rate_id"],
                    bill["bill_month"],
                    bill["units_used"],
                    bill["amount_due"],
                    bill["outstanding_amount"],
                    bill["status"],
                    bill["due_date"],
                    bill["bill_id"],
                ),
            )
        else:
            execute_mysql(
                """
                INSERT INTO bills
                (bill_id, customer_id, usage_id, rate_id, bill_month, units_used, amount_due, outstanding_amount, status, due_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    bill["bill_id"],
                    secondary_customer["customer_id"],
                    bill["usage_id"],
                    bill["rate_id"],
                    bill["bill_month"],
                    bill["units_used"],
                    bill["amount_due"],
                    bill["outstanding_amount"],
                    bill["status"],
                    bill["due_date"],
                ),
            )
        print("MYSQL SYNC OK: bills", bill_id)
    except Exception as e:
        print("MYSQL SYNC ERROR in sync_bill_to_secondary:", e)


def sync_payment_to_secondary(payment_id):
    try:
        if not mysql_available():
            print("MYSQL NOT AVAILABLE: sync_payment_to_secondary")
            return

        payment = fetch_one_pg(
            """
            SELECT p.payment_id, p.amount_paid, p.payment_method, p.payment_reference,
                   p.payment_gateway, p.payment_status, p.payment_date,
                   c.account_number, b.bill_id
            FROM payments p
            JOIN customers c ON c.customer_id = p.customer_id
            JOIN bills b ON b.bill_id = p.bill_id
            WHERE p.payment_id = %s
            """,
            (payment_id,),
        )
        if not payment:
            print("PAYMENT NOT FOUND IN POSTGRES:", payment_id)
            return

        secondary_customer = fetch_one_mysql(
            "SELECT customer_id FROM customers WHERE account_number = %s",
            (payment["account_number"],)
        )
        if not secondary_customer:
            print("MYSQL CUSTOMER NOT FOUND FOR PAYMENT:", payment["account_number"])
            return

        existing = fetch_one_mysql("SELECT payment_id FROM payments WHERE payment_id = %s", (payment["payment_id"],))
        if existing:
            execute_mysql(
                """
                UPDATE payments
                SET bill_id=%s, customer_id=%s, amount_paid=%s, payment_method=%s,
                    payment_reference=%s, payment_gateway=%s, payment_status=%s, payment_date=%s
                WHERE payment_id=%s
                """,
                (
                    payment["bill_id"],
                    secondary_customer["customer_id"],
                    payment["amount_paid"],
                    payment["payment_method"],
                    payment["payment_reference"],
                    payment["payment_gateway"],
                    payment["payment_status"],
                    payment["payment_date"],
                    payment["payment_id"],
                ),
            )
        else:
            execute_mysql(
                """
                INSERT INTO payments
                (payment_id, bill_id, customer_id, amount_paid, payment_method, payment_reference, payment_gateway, payment_status, payment_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    payment["payment_id"],
                    payment["bill_id"],
                    secondary_customer["customer_id"],
                    payment["amount_paid"],
                    payment["payment_method"],
                    payment["payment_reference"],
                    payment["payment_gateway"],
                    payment["payment_status"],
                    payment["payment_date"],
                ),
            )
        print("MYSQL SYNC OK: payments", payment_id)
    except Exception as e:
        print("MYSQL SYNC ERROR in sync_payment_to_secondary:", e)


# --------------------------
# Business data helpers
# --------------------------
def get_public_stats():
    return {
        "total_customers": int(scalar_pg("SELECT COUNT(*) FROM customers") or 0),
        "total_branches": int(scalar_pg("SELECT COUNT(*) FROM branches") or 0),
        "unresolved_leaks": int(scalar_pg("SELECT COUNT(*) FROM leak_reports WHERE COALESCE(status, 'Pending') <> 'Resolved'") or 0),
        "unpaid_bills": int(scalar_pg("SELECT COUNT(*) FROM bills WHERE COALESCE(status, 'Unpaid') <> 'Paid'") or 0),
    }


def get_branches():
    return fetch_all_pg("SELECT * FROM branches ORDER BY branch_name")


def get_customer_dashboard_data(customer_id):
    customer = fetch_one_pg("SELECT * FROM customers WHERE customer_id = %s", (customer_id,))
    bills = fetch_all_pg("SELECT * FROM bills WHERE customer_id = %s ORDER BY bill_month DESC, bill_id DESC", (customer_id,))
    usage = fetch_all_pg("SELECT * FROM water_usage WHERE customer_id = %s ORDER BY usage_month DESC, usage_id DESC", (customer_id,))
    payments = fetch_all_pg("SELECT * FROM payments WHERE customer_id = %s ORDER BY payment_date DESC, payment_id DESC", (customer_id,))
    requests = fetch_all_pg("SELECT * FROM service_requests WHERE customer_id = %s ORDER BY created_at DESC, request_id DESC", (customer_id,))
    leaks = fetch_all_pg("SELECT * FROM leak_reports WHERE customer_id = %s ORDER BY reported_at DESC, report_id DESC", (customer_id,))

    total_billed = sum(safe_decimal(row["amount_due"]) for row in bills) if bills else Decimal("0")
    outstanding = sum(safe_decimal(row["outstanding_amount"]) for row in bills) if bills else Decimal("0")
    total_paid = sum(safe_decimal(row["amount_paid"]) for row in payments) if payments else Decimal("0")
    return customer, bills, usage, payments, requests, leaks, total_billed, outstanding, total_paid


def get_admin_dashboard_data():
    metrics = fetch_one_pg(
        """
        SELECT
            (SELECT COUNT(*) FROM customers) AS total_customers,
            (SELECT COUNT(*) FROM bills) AS total_bills,
            (SELECT COALESCE(SUM(amount_paid), 0) FROM payments) AS total_collections,
            (SELECT COALESCE(SUM(outstanding_amount), 0) FROM bills) AS outstanding_balance,
            (SELECT COUNT(*) FROM leak_reports WHERE COALESCE(status,'Pending') <> 'Resolved') AS open_leaks,
            (SELECT COUNT(*) FROM service_requests WHERE COALESCE(status,'Open') <> 'Resolved') AS open_requests
        """
    )
    recent_bills = fetch_all_pg(
        """
        SELECT b.bill_id, c.account_number, c.first_name, c.last_name, b.bill_month, b.amount_due, b.outstanding_amount, b.status
        FROM bills b
        JOIN customers c ON c.customer_id = b.customer_id
        ORDER BY b.bill_id DESC
        LIMIT 10
        """
    )
    recent_payments = fetch_all_pg(
        """
        SELECT p.payment_id, c.account_number, c.first_name, c.last_name, p.amount_paid, p.payment_method, p.payment_status, p.payment_date
        FROM payments p
        JOIN customers c ON c.customer_id = p.customer_id
        ORDER BY p.payment_id DESC
        LIMIT 10
        """
    )
    leaks = fetch_all_pg("SELECT * FROM leak_reports ORDER BY report_id DESC LIMIT 10")
    requests = fetch_all_pg("SELECT * FROM service_requests ORDER BY request_id DESC LIMIT 10")
    customers = fetch_all_pg("SELECT * FROM customers ORDER BY customer_id DESC")
    users = fetch_all_pg("SELECT * FROM users ORDER BY user_id DESC")
    usage = fetch_all_pg(
        """
        SELECT w.usage_id, w.customer_id, w.usage_month, w.units_used, c.account_number, c.first_name, c.last_name
        FROM water_usage w
        JOIN customers c ON c.customer_id = w.customer_id
        LEFT JOIN bills b ON b.usage_id = w.usage_id
        WHERE b.bill_id IS NULL
        ORDER BY w.usage_id DESC
        """
    )
    return metrics, recent_bills, recent_payments, leaks, requests, customers, users, usage


def get_manager_dashboard_data(branch_id=None):
    filters = ""
    params = []
    if branch_id:
        filters = "WHERE c.branch_id = %s"
        params.append(branch_id)

    metrics = fetch_one_pg(
        f"""
        SELECT
            COUNT(DISTINCT c.customer_id) AS total_customers,
            COALESCE(SUM(w.units_used), 0) AS monthly_units,
            COALESCE(SUM(b.amount_due), 0) AS billed_amount,
            COALESCE(SUM(b.outstanding_amount), 0) AS outstanding_amount
        FROM customers c
        LEFT JOIN water_usage w ON w.customer_id = c.customer_id
            AND date_trunc('month', w.usage_month) = date_trunc('month', CURRENT_DATE)
        LEFT JOIN bills b ON b.customer_id = c.customer_id
            AND date_trunc('month', b.bill_month) = date_trunc('month', CURRENT_DATE)
        {filters}
        """,
        tuple(params),
    )

    trends = fetch_one_pg(
        f"""
        SELECT
            COALESCE(SUM(CASE WHEN w.usage_month >= CURRENT_DATE - INTERVAL '1 day' THEN w.units_used ELSE 0 END), 0) AS daily,
            COALESCE(SUM(CASE WHEN w.usage_month >= CURRENT_DATE - INTERVAL '7 day' THEN w.units_used ELSE 0 END), 0) AS weekly,
            COALESCE(SUM(CASE WHEN w.usage_month >= CURRENT_DATE - INTERVAL '1 month' THEN w.units_used ELSE 0 END), 0) AS monthly,
            COALESCE(SUM(CASE WHEN w.usage_month >= CURRENT_DATE - INTERVAL '3 month' THEN w.units_used ELSE 0 END), 0) AS quarterly,
            COALESCE(SUM(CASE WHEN w.usage_month >= CURRENT_DATE - INTERVAL '1 year' THEN w.units_used ELSE 0 END), 0) AS yearly
        FROM water_usage w
        JOIN customers c ON c.customer_id = w.customer_id
        {filters}
        """,
        tuple(params),
    )

    districts = fetch_all_pg(
        f"""
        SELECT c.district,
               COUNT(DISTINCT c.customer_id) AS customers,
               COALESCE(SUM(w.units_used), 0) AS units_used,
               COALESCE(SUM(b.amount_due), 0) AS billed,
               COALESCE(SUM(b.outstanding_amount), 0) AS outstanding
        FROM customers c
        LEFT JOIN water_usage w ON w.customer_id = c.customer_id
        LEFT JOIN bills b ON b.customer_id = c.customer_id
        {filters}
        GROUP BY c.district
        ORDER BY c.district
        """,
        tuple(params),
    )

    top_customers = fetch_all_pg(
        f"""
        SELECT c.account_number, c.first_name, c.last_name,
               COALESCE(SUM(w.units_used), 0) AS total_units,
               COALESCE(SUM(b.outstanding_amount), 0) AS outstanding
        FROM customers c
        LEFT JOIN water_usage w ON w.customer_id = c.customer_id
        LEFT JOIN bills b ON b.customer_id = c.customer_id
        {filters}
        GROUP BY c.customer_id, c.account_number, c.first_name, c.last_name
        ORDER BY total_units DESC
        LIMIT 10
        """,
        tuple(params),
    )

    branch = None
    if branch_id:
        branch = fetch_one_pg("SELECT * FROM branches WHERE branch_id = %s", (branch_id,))
    return metrics, trends, districts, top_customers, branch


def get_distributed_counts():
    primary = {
        "customers": int(scalar_pg("SELECT COUNT(*) FROM customers") or 0),
        "usage_records": int(scalar_pg("SELECT COUNT(*) FROM water_usage") or 0),
        "bills": int(scalar_pg("SELECT COUNT(*) FROM bills") or 0),
        "payments": int(scalar_pg("SELECT COUNT(*) FROM payments") or 0),
    }
    try:
        secondary = {
            "customers": int(scalar_mysql("SELECT COUNT(*) FROM customers") or 0),
            "usage_records": int(scalar_mysql("SELECT COUNT(*) FROM water_usage") or 0),
            "bills": int(scalar_mysql("SELECT COUNT(*) FROM bills") or 0),
            "payments": int(scalar_mysql("SELECT COUNT(*) FROM payments") or 0),
        }
    except Exception:
        secondary = {"customers": 0, "usage_records": 0, "bills": 0, "payments": 0}
    return primary, secondary


def recalc_bill_status(outstanding_amount):
    outstanding = safe_decimal(outstanding_amount)
    if outstanding <= Decimal("0"):
        return Decimal("0.00"), "Paid"
    return outstanding, "Partially Paid"


# --------------------------
# Routes: public
# --------------------------
@app.route("/")
def home():
    return render_template("index.html", stats=get_public_stats(), branches=get_branches())


@app.route("/services")
def services():
    return render_template("services.html")


@app.route("/contact")
def contact():
    return render_template("contact.html", branches=get_branches())


@app.route("/check-bill", methods=["GET", "POST"])
def check_bill():
    result = None
    if request.method == "POST":
        account_number = request.form.get("account_number", "").strip()
        if account_number:
            result = fetch_all_pg(
                """
                SELECT c.account_number, c.first_name, c.last_name,
                       b.bill_month, b.amount_due, b.outstanding_amount, b.status, b.due_date
                FROM bills b
                JOIN customers c ON c.customer_id = b.customer_id
                WHERE c.account_number = %s
                ORDER BY b.bill_month DESC, b.bill_id DESC
                """,
                (account_number,),
            )
            if not result:
                flash("No bill records were found for that account number.", "warning")
    return render_template("check_bill.html", result=result)


@app.route("/report-leak", methods=["GET", "POST"])
def report_leak():
    if request.method == "POST":
        account_number = request.form.get("account_number", "").strip()
        customer_id = None
        if account_number:
            customer = fetch_one_pg("SELECT customer_id FROM customers WHERE account_number = %s", (account_number,))
            customer_id = customer["customer_id"] if customer else None

        execute_pg(
            """
            INSERT INTO leak_reports (customer_id, location, description, priority, status)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                customer_id,
                request.form.get("location", "").strip(),
                request.form.get("description", "").strip(),
                request.form.get("priority", "Medium").strip(),
                "Pending",
            ),
        )
        flash("Leak report submitted successfully.", "success")
        return redirect(url_for("report_leak"))
    return render_template("report_leak.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    branches = get_branches()
    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        full_name = f"{first_name} {last_name}".strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        account_number = request.form.get("account_number", "").strip()
        meter_number = request.form.get("meter_number", "").strip()
        district = request.form.get("district", "").strip()
        customer_type = request.form.get("customer_type", "Domestic").strip()
        branch_id = request.form.get("branch_id") or None
        address = request.form.get("address", "").strip()
        password = request.form.get("password", "")

        if fetch_one_pg("SELECT user_id FROM users WHERE email = %s", (email,)):
            flash("That email is already registered.", "danger")
            return render_template("register.html", branches=branches)
        if fetch_one_pg("SELECT customer_id FROM customers WHERE account_number = %s", (account_number,)):
            flash("That account number already exists.", "danger")
            return render_template("register.html", branches=branches)
        if fetch_one_pg("SELECT customer_id FROM customers WHERE meter_number = %s", (meter_number,)):
            flash("That meter number already exists.", "danger")
            return render_template("register.html", branches=branches)

        password_hash = generate_password_hash(password)
        user_row = execute_pg(
            """
            INSERT INTO users (full_name, email, password_hash, role, branch_id, is_active)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING user_id
            """,
            (full_name, email, password_hash, "customer", branch_id, True),
            fetch=True,
        )
        user_id = user_row["user_id"]
        customer_row = execute_pg(
            """
            INSERT INTO customers (user_id, branch_id, account_number, meter_number, first_name, last_name, email, phone, district, address, customer_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING customer_id
            """,
            (user_id, branch_id, account_number, meter_number, first_name, last_name, email, phone, district, address, customer_type),
            fetch=True,
        )
        sync_user_to_secondary(user_id)
        sync_customer_to_secondary(customer_row["customer_id"])
        log_action(user_id, "customer_registered", f"Customer account {account_number} created")
        flash("Customer account created successfully. You can now sign in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html", branches=branches)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = fetch_one_pg("SELECT * FROM users WHERE email = %s AND is_active = TRUE", (email,))

        if not user or not verify_password(user.get("password_hash"), password):
            flash("Invalid email or password.", "danger")
            return render_template("login.html")

        customer = None
        if user["role"] == "customer":
            customer = fetch_one_pg("SELECT customer_id FROM customers WHERE user_id = %s", (user["user_id"],))

        session["user"] = {
            "user_id": user["user_id"],
            "full_name": user["full_name"],
            "email": user["email"],
            "role": user["role"],
            "branch_id": user.get("branch_id"),
            "customer_id": customer["customer_id"] if customer else None,
        }
        log_action(user["user_id"], "login", f"{user['role']} signed in")

        next_url = request.args.get("next")
        if next_url:
            return redirect(next_url)
        if user["role"] == "admin":
            return redirect(url_for("admin_dashboard"))
        if user["role"] == "manager":
            return redirect(url_for("manager_dashboard"))
        return redirect(url_for("customer_dashboard"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    user = current_user()
    if user:
        log_action(user["user_id"], "logout", "User signed out")
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("home"))


# --------------------------
# Routes: customer
# --------------------------
@app.route("/customer")
@login_required("customer")
def customer_dashboard():
    customer_id = current_user().get("customer_id")
    if not customer_id:
        flash("Customer profile is not linked to this account.", "danger")
        return redirect(url_for("logout"))
    customer, bills, usage, payments, requests_data, leaks, total_billed, outstanding, total_paid = get_customer_dashboard_data(customer_id)
    return render_template(
        "customer_dashboard.html",
        customer=customer,
        bills=bills,
        usage=usage,
        payments=payments,
        requests=requests_data,
        leaks=leaks,
        total_billed=total_billed,
        outstanding=outstanding,
        total_paid=total_paid,
    )


@app.route("/customer/request", methods=["POST"])
@login_required("customer")
def customer_request():
    customer_id = current_user()["customer_id"]
    execute_pg(
        """
        INSERT INTO service_requests (customer_id, request_type, description, status)
        VALUES (%s, %s, %s, %s)
        """,
        (
            customer_id,
            request.form.get("request_type", "Service Request").strip(),
            request.form.get("description", "").strip(),
            "Open",
        ),
    )
    log_action(current_user()["user_id"], "service_request_created", f"Customer {customer_id} created request")
    flash("Service request submitted successfully.", "success")
    return redirect(url_for("customer_dashboard"))


@app.route("/customer/leak", methods=["POST"])
@login_required("customer")
def customer_leak():
    customer_id = current_user()["customer_id"]
    execute_pg(
        """
        INSERT INTO leak_reports (customer_id, location, description, priority, status)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            customer_id,
            request.form.get("location", "").strip(),
            request.form.get("description", "").strip(),
            request.form.get("priority", "Medium").strip(),
            "Pending",
        ),
    )
    log_action(current_user()["user_id"], "customer_leak_reported", f"Customer {customer_id} submitted leak report")
    flash("Leak report submitted.", "success")
    return redirect(url_for("customer_dashboard"))


@app.route("/customer/chat")
@login_required("customer")
def customer_chat():
    if not sendbird_enabled():
        return jsonify({"ok": False, "error": "Sendbird is not configured on the server."}), 500

    customer_id = current_user().get("customer_id")
    customer = fetch_one_pg("SELECT * FROM customers WHERE customer_id = %s", (customer_id,))
    if not customer:
        return jsonify({"ok": False, "error": "Customer profile not found."}), 404

    try:
        channel = get_or_create_support_channel(customer)
        messages_data = list_channel_messages(channel["channel_url"])
        messages = messages_data.get("messages", [])
        return jsonify({
            "ok": True,
            "channel_url": channel["channel_url"],
            "messages": messages,
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/customer/chat/send", methods=["POST"])
@login_required("customer")
def customer_chat_send():
    if not sendbird_enabled():
        return jsonify({"ok": False, "error": "Sendbird is not configured on the server."}), 500

    customer_id = current_user().get("customer_id")
    customer = fetch_one_pg("SELECT * FROM customers WHERE customer_id = %s", (customer_id,))
    if not customer:
        return jsonify({"ok": False, "error": "Customer profile not found."}), 404

    message = request.form.get("message", "").strip()
    if not message:
        return jsonify({"ok": False, "error": "Message is required."}), 400

    try:
        channel = get_or_create_support_channel(customer)
        sender_id = get_sendbird_customer_user_id(customer)
        sent = send_user_message(channel["channel_url"], sender_id, message)
        return jsonify({"ok": True, "message": sent})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/payments/checkout/<int:bill_id>", methods=["POST"])
@login_required("customer")
def payment_checkout(bill_id):
    bill = fetch_one_pg(
        "SELECT * FROM bills WHERE bill_id = %s AND customer_id = %s",
        (bill_id, current_user()["customer_id"]),
    )
    if not bill:
        flash("Bill not found.", "danger")
        return redirect(url_for("customer_dashboard"))

    info = payment_gateway.initiate(bill, current_user())
    flash(
        f"Checkout initiated with {info['provider']} in {info['mode']} mode. Reference: {info['checkout_reference']}",
        "success",
    )
    return redirect(url_for("customer_dashboard"))


@app.route("/payments/callback")
def payment_callback():
    reference = request.args.get("reference", "")
    status = request.args.get("status", "received")
    flash(f"Gateway callback received for {reference} with status: {status}", "info")
    return redirect(url_for("customer_dashboard") if current_user() and current_user().get("role") == "customer" else url_for("home"))


@app.route("/payments/record", methods=["POST"])
@login_required("customer", "admin")
def record_payment():
    bill_id = int(request.form.get("bill_id"))
    amount_paid = safe_decimal(request.form.get("amount_paid", "0"))
    payment_method = request.form.get("payment_method", "Manual")
    payment_reference = request.form.get("payment_reference", "").strip() or None
    payment_gateway_name = request.form.get("payment_gateway", PAYMENT_PROVIDER_NAME).strip() or None

    bill = fetch_one_pg("SELECT * FROM bills WHERE bill_id = %s", (bill_id,))
    if not bill:
        flash("Bill not found.", "danger")
        return redirect(url_for("customer_dashboard") if current_user()["role"] == "customer" else url_for("admin_dashboard"))

    if current_user()["role"] == "customer" and bill["customer_id"] != current_user()["customer_id"]:
        abort(403)

    new_outstanding = safe_decimal(bill["outstanding_amount"]) - amount_paid
    adjusted_outstanding, status = recalc_bill_status(new_outstanding)

    payment_row = execute_pg(
        """
        INSERT INTO payments (bill_id, customer_id, amount_paid, payment_method, payment_reference, payment_gateway, payment_status)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING payment_id
        """,
        (
            bill_id,
            bill["customer_id"],
            amount_paid,
            payment_method,
            payment_reference,
            payment_gateway_name,
            "Completed",
        ),
        fetch=True,
    )
    execute_pg(
        "UPDATE bills SET outstanding_amount = %s, status = %s WHERE bill_id = %s",
        (adjusted_outstanding, status, bill_id),
    )
    sync_payment_to_secondary(payment_row["payment_id"])
    sync_bill_to_secondary(bill_id)
    log_action(current_user()["user_id"], "payment_recorded", f"Payment for bill {bill_id}: {amount_paid}")
    flash("Payment recorded successfully.", "success")
    return redirect(url_for("customer_dashboard") if current_user()["role"] == "customer" else url_for("admin_dashboard"))


# --------------------------
# Routes: admin
# --------------------------
def admin_context_data():
    return {
        "branches": get_branches(),
        "customer_types": ["Domestic", "Commercial", "Institutional"],
        "user_roles": ["admin", "manager", "customer"],
    }


@app.route("/admin/users", methods=["GET", "POST"])
@login_required("admin")
def admin_users():
    context = admin_context_data()
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "customer").strip()
        branch_id = request.form.get("branch_id") or None

        if fetch_one_pg("SELECT user_id FROM users WHERE email = %s", (email,)):
            flash("A user with that email already exists.", "danger")
            users = fetch_all_pg("SELECT * FROM users ORDER BY user_id DESC")
            return render_template("admin_users.html", users=users, **context)

        row = execute_pg(
            """
            INSERT INTO users (full_name, email, password_hash, role, branch_id, is_active)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING user_id
            """,
            (full_name, email, generate_password_hash(password), role, branch_id, True),
            fetch=True,
        )
        sync_user_to_secondary(row["user_id"])
        log_action(current_user()["user_id"], "user_created", f"User {row['user_id']} created")
        flash("User account created successfully.", "success")
        return redirect(url_for("admin_users"))

    users = fetch_all_pg(
        """
        SELECT u.*, b.branch_name
        FROM users u
        LEFT JOIN branches b ON b.branch_id = u.branch_id
        ORDER BY u.user_id DESC
        """
    )
    return render_template("admin_users.html", users=users, **context)


@app.route("/admin/users/<int:user_id>/toggle", methods=["POST"])
@login_required("admin")
def admin_toggle_user(user_id):
    user = fetch_one_pg("SELECT * FROM users WHERE user_id = %s", (user_id,))
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("admin_users"))
    new_status = not bool(user["is_active"])
    execute_pg("UPDATE users SET is_active = %s WHERE user_id = %s", (new_status, user_id))
    sync_user_to_secondary(user_id)
    flash("User status updated successfully.", "success")
    return redirect(url_for("admin_users"))


@app.route("/admin/customers", methods=["GET", "POST"])
@login_required("admin")
def admin_customers():
    context = admin_context_data()
    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        account_number = request.form.get("account_number", "").strip()
        meter_number = request.form.get("meter_number", "").strip()
        district = request.form.get("district", "").strip()
        address = request.form.get("address", "").strip()
        customer_type = request.form.get("customer_type", "Domestic").strip()
        branch_id = request.form.get("branch_id") or None
        user_id = request.form.get("user_id") or None

        if fetch_one_pg("SELECT customer_id FROM customers WHERE email = %s", (email,)):
            flash("A customer with that email already exists.", "danger")
        elif fetch_one_pg("SELECT customer_id FROM customers WHERE account_number = %s", (account_number,)):
            flash("That account number already exists.", "danger")
        elif fetch_one_pg("SELECT customer_id FROM customers WHERE meter_number = %s", (meter_number,)):
            flash("That meter number already exists.", "danger")
        else:
            row = execute_pg(
                """
                INSERT INTO customers (user_id, branch_id, account_number, meter_number, first_name, last_name, email, phone, district, address, customer_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING customer_id
                """,
                (user_id, branch_id, account_number, meter_number, first_name, last_name, email, phone, district, address, customer_type),
                fetch=True,
            )
            sync_customer_to_secondary(row["customer_id"])
            log_action(current_user()["user_id"], "customer_created_by_admin", f"Customer {row['customer_id']} created")
            flash("Customer added successfully.", "success")
            return redirect(url_for("admin_customers"))

    customers = fetch_all_pg(
        """
        SELECT c.*, b.branch_name, u.full_name AS linked_user_name
        FROM customers c
        LEFT JOIN branches b ON b.branch_id = c.branch_id
        LEFT JOIN users u ON u.user_id = c.user_id
        ORDER BY c.customer_id DESC
        """
    )
    linkable_users = fetch_all_pg(
        """
        SELECT u.user_id, u.full_name, u.email
        FROM users u
        LEFT JOIN customers c ON c.user_id = u.user_id
        WHERE u.role = 'customer' AND c.customer_id IS NULL
        ORDER BY u.full_name
        """
    )
    return render_template("admin_customers.html", customers=customers, linkable_users=linkable_users, **context)


@app.route("/admin/customers/<int:customer_id>/edit", methods=["POST"])
@login_required("admin")
def admin_edit_customer(customer_id):
    customer = fetch_one_pg("SELECT * FROM customers WHERE customer_id = %s", (customer_id,))
    if not customer:
        flash("Customer not found.", "danger")
        return redirect(url_for("admin_customers"))

    email = request.form.get("email", "").strip().lower()
    account_number = request.form.get("account_number", "").strip()
    meter_number = request.form.get("meter_number", "").strip()

    if fetch_one_pg("SELECT customer_id FROM customers WHERE email = %s AND customer_id <> %s", (email, customer_id)):
        flash("Another customer already uses that email.", "danger")
        return redirect(url_for("admin_customers"))
    if fetch_one_pg("SELECT customer_id FROM customers WHERE account_number = %s AND customer_id <> %s", (account_number, customer_id)):
        flash("Another customer already uses that account number.", "danger")
        return redirect(url_for("admin_customers"))
    if fetch_one_pg("SELECT customer_id FROM customers WHERE meter_number = %s AND customer_id <> %s", (meter_number, customer_id)):
        flash("Another customer already uses that meter number.", "danger")
        return redirect(url_for("admin_customers"))

    execute_pg(
        """
        UPDATE customers
        SET branch_id=%s, account_number=%s, meter_number=%s, first_name=%s, last_name=%s, email=%s,
            phone=%s, district=%s, address=%s, customer_type=%s
        WHERE customer_id=%s
        """,
        (
            request.form.get("branch_id") or None,
            account_number,
            meter_number,
            request.form.get("first_name", "").strip(),
            request.form.get("last_name", "").strip(),
            email,
            request.form.get("phone", "").strip(),
            request.form.get("district", "").strip(),
            request.form.get("address", "").strip(),
            request.form.get("customer_type", "Domestic").strip(),
            customer_id,
        ),
    )
    sync_customer_to_secondary(customer_id)
    flash("Customer updated successfully.", "success")
    return redirect(url_for("admin_customers"))


@app.route("/admin/bills")
@login_required("admin")
def admin_bills():
    metrics = fetch_one_pg(
        """
        SELECT COUNT(*) AS total_bills, COALESCE(SUM(amount_due),0) AS total_amount,
               COALESCE(SUM(outstanding_amount),0) AS outstanding_amount
        FROM bills
        """
    )
    bills = fetch_all_pg(
        """
        SELECT b.bill_id, b.bill_month, b.units_used, b.amount_due, b.outstanding_amount, b.status, b.due_date,
               c.account_number, c.first_name, c.last_name
        FROM bills b
        JOIN customers c ON c.customer_id = b.customer_id
        ORDER BY b.bill_id DESC
        """
    )
    payable_bills = fetch_all_pg(
        """
        SELECT b.bill_id, c.account_number, c.first_name, c.last_name, b.outstanding_amount
        FROM bills b
        JOIN customers c ON c.customer_id = b.customer_id
        WHERE b.outstanding_amount > 0
        ORDER BY b.bill_id DESC
        """
    )
    return render_template("admin_bills.html", metrics=metrics, bills=bills, payable_bills=payable_bills)


@app.route("/admin/operations")
@login_required("admin")
def admin_operations():
    metrics, recent_bills, recent_payments, leaks, requests_data, customers, users, usage = get_admin_dashboard_data()
    return render_template(
        "admin_operations.html",
        metrics=metrics,
        recent_bills=recent_bills,
        recent_payments=recent_payments,
        leaks=leaks,
        requests=requests_data,
        customers=customers,
        users=users,
        usage=usage,
        branches=get_branches(),
    )


@app.route("/admin")
@login_required("admin")
def admin_dashboard():
    metrics, recent_bills, recent_payments, leaks, requests_data, customers, users, usage = get_admin_dashboard_data()
    return render_template(
        "admin_dashboard.html",
        branches=get_branches(),
        metrics=metrics,
        recent_bills=recent_bills,
        recent_payments=recent_payments,
        leaks=leaks,
        requests=requests_data,
        customers=customers,
        users=users,
        usage=usage,
    )


@app.route("/admin/usage", methods=["POST"])
@login_required("admin")
def admin_add_usage():
    customer_id = int(request.form.get("customer_id"))
    usage_month = request.form.get("usage_month")
    previous_reading = safe_decimal(request.form.get("previous_reading", "0"))
    current_reading = safe_decimal(request.form.get("current_reading", "0"))

    if current_reading < previous_reading:
        flash("Current reading cannot be lower than previous reading.", "danger")
        return redirect(url_for("admin_dashboard"))

    units_used = current_reading - previous_reading
    usage_row = execute_pg(
        """
        INSERT INTO water_usage (customer_id, usage_month, previous_reading, current_reading, units_used)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING usage_id
        """,
        (customer_id, usage_month, previous_reading, current_reading, units_used),
        fetch=True,
    )
    sync_usage_to_secondary(usage_row["usage_id"])
    log_action(current_user()["user_id"], "usage_added", f"Usage {usage_row['usage_id']} added for customer {customer_id}")
    flash("Water usage record added successfully.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/bill/generate", methods=["POST"])
@login_required("admin")
def admin_generate_bill():
    usage_id = int(request.form.get("usage_id"))
    usage = fetch_one_pg(
        """
        SELECT w.*, c.customer_id
        FROM water_usage w
        JOIN customers c ON c.customer_id = w.customer_id
        WHERE w.usage_id = %s
        """,
        (usage_id,),
    )
    if not usage:
        flash("Usage record not found.", "danger")
        return redirect(url_for("admin_dashboard"))

    existing = fetch_one_pg("SELECT bill_id FROM bills WHERE usage_id = %s", (usage_id,))
    if existing:
        flash("A bill already exists for that usage record.", "warning")
        return redirect(url_for("admin_dashboard"))

    rate = fetch_one_pg(
        """
        SELECT *
        FROM billing_rates
        WHERE active_status = 'Active'
          AND %s BETWEEN min_units AND max_units
        ORDER BY min_units ASC
        LIMIT 1
        """,
        (usage["units_used"],),
    )
    if not rate:
        flash("No active billing rate matches this usage amount.", "danger")
        return redirect(url_for("admin_dashboard"))

    amount_due = (safe_decimal(usage["units_used"]) * safe_decimal(rate["price_per_unit"])) + safe_decimal(rate["fixed_charge"])
    due_date = date.today() + timedelta(days=21)

    bill_row = execute_pg(
        """
        INSERT INTO bills (customer_id, usage_id, rate_id, bill_month, units_used, amount_due, outstanding_amount, status, due_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING bill_id
        """,
        (
            usage["customer_id"],
            usage_id,
            rate["rate_id"],
            usage["usage_month"],
            usage["units_used"],
            amount_due,
            amount_due,
            "Unpaid",
            due_date,
        ),
        fetch=True,
    )
    sync_rate_to_secondary(rate["rate_id"])
    sync_bill_to_secondary(bill_row["bill_id"])
    log_action(current_user()["user_id"], "bill_generated", f"Bill {bill_row['bill_id']} generated from usage {usage_id}")
    flash("Bill generated successfully.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/rates", methods=["POST"])
@login_required("admin")
def admin_add_rate():
    row = execute_pg(
        """
        INSERT INTO billing_rates (rate_tier, min_units, max_units, price_per_unit, fixed_charge, effective_from, active_status)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING rate_id
        """,
        (
            request.form.get("rate_tier", "").strip(),
            safe_decimal(request.form.get("min_units", "0")),
            safe_decimal(request.form.get("max_units", "0")),
            safe_decimal(request.form.get("price_per_unit", "0")),
            safe_decimal(request.form.get("fixed_charge", "0")),
            request.form.get("effective_from"),
            request.form.get("active_status", "Active").strip(),
        ),
        fetch=True,
    )
    sync_rate_to_secondary(row["rate_id"])
    log_action(current_user()["user_id"], "billing_rate_added", f"Rate {row['rate_id']} created")
    flash("Billing rate saved successfully.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/notification", methods=["POST"])
@login_required("admin")
def admin_notification():
    execute_pg(
        """
        INSERT INTO notifications (customer_id, bill_id, channel, subject, message, sent_status)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            None,
            None,
            request.form.get("channel", "Portal").strip(),
            request.form.get("subject", "").strip(),
            request.form.get("message", "").strip(),
            "Pending",
        ),
    )
    log_action(current_user()["user_id"], "notification_created", "Notification saved")
    flash("Notification saved successfully.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/leak/<int:report_id>", methods=["POST"])
@login_required("admin")
def admin_update_leak(report_id):
    status = request.form.get("status", "Pending").strip()
    resolved_at = datetime.now() if status == "Resolved" else None
    execute_pg("UPDATE leak_reports SET status = %s, resolved_at = %s WHERE report_id = %s", (status, resolved_at, report_id))
    flash("Leak report updated.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/request/<int:request_id>", methods=["POST"])
@login_required("admin")
def admin_update_request(request_id):
    status = request.form.get("status", "Open").strip()
    execute_pg(
        "UPDATE service_requests SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE request_id = %s",
        (status, request_id),
    )
    flash("Service request updated.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/test-mysql")
def test_mysql():
    try:
        conn = get_mysql_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT DATABASE() AS database_name, NOW() AS server_time")
            row = cur.fetchone()
        conn.close()
        return jsonify({"ok": True, "result": row})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/test-mysql-insert")
def test_mysql_insert():
    try:
        execute_mysql(
            """
            INSERT INTO users (full_name, email, password_hash, role, branch_id, is_active)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                "Debug User",
                f"debug_{int(datetime.now().timestamp())}@test.com",
                "debug_hash",
                "customer",
                None,
                True,
            ),
        )
        return jsonify({"ok": True, "message": "Insert worked"})
    except Exception as e:
        print("TEST MYSQL INSERT ERROR:", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/admin/backfill-mysql", methods=["GET", "POST"])
@login_required("admin")
def admin_backfill_mysql():
    try:
        print("BACKFILL STARTED")

        if not mysql_available():
            print("BACKFILL FAILED: MySQL not available")
            flash("MySQL is not available.", "danger")
            return redirect(url_for("admin_dashboard"))

        users = fetch_all_pg("SELECT user_id FROM users ORDER BY user_id")
        print("USERS TO SYNC:", len(users))
        for row in users:
            try:
                sync_user_to_secondary(row["user_id"])
            except Exception as e:
                print("BACKFILL USER ERROR:", row["user_id"], e)

        customers = fetch_all_pg("SELECT customer_id FROM customers ORDER BY customer_id")
        print("CUSTOMERS TO SYNC:", len(customers))
        for row in customers:
            try:
                sync_customer_to_secondary(row["customer_id"])
            except Exception as e:
                print("BACKFILL CUSTOMER ERROR:", row["customer_id"], e)

        rates = fetch_all_pg("SELECT rate_id FROM billing_rates ORDER BY rate_id")
        print("RATES TO SYNC:", len(rates))
        for row in rates:
            try:
                sync_rate_to_secondary(row["rate_id"])
            except Exception as e:
                print("BACKFILL RATE ERROR:", row["rate_id"], e)

        usage_rows = fetch_all_pg("SELECT usage_id FROM water_usage ORDER BY usage_id")
        print("USAGE ROWS TO SYNC:", len(usage_rows))
        for row in usage_rows:
            try:
                sync_usage_to_secondary(row["usage_id"])
            except Exception as e:
                print("BACKFILL USAGE ERROR:", row["usage_id"], e)

        bills = fetch_all_pg("SELECT bill_id FROM bills ORDER BY bill_id")
        print("BILLS TO SYNC:", len(bills))
        for row in bills:
            try:
                sync_bill_to_secondary(row["bill_id"])
            except Exception as e:
                print("BACKFILL BILL ERROR:", row["bill_id"], e)

        payments = fetch_all_pg("SELECT payment_id FROM payments ORDER BY payment_id")
        print("PAYMENTS TO SYNC:", len(payments))
        for row in payments:
            try:
                sync_payment_to_secondary(row["payment_id"])
            except Exception as e:
                print("BACKFILL PAYMENT ERROR:", row["payment_id"], e)

        print("BACKFILL COMPLETED")
        flash("MySQL backfill completed successfully.", "success")
        return redirect(url_for("admin_dashboard"))

    except Exception as e:
        print("BACKFILL FATAL ERROR:", e)
        flash(f"MySQL backfill failed: {e}", "danger")
        return redirect(url_for("admin_dashboard"))


# --------------------------
# Routes: manager
# --------------------------
@app.route("/manager")
@login_required("manager", "admin")
def manager_dashboard():
    user = current_user()
    branch_id = user.get("branch_id") if user.get("role") == "manager" else request.args.get("branch_id")
    if branch_id:
        try:
            branch_id = int(branch_id)
        except ValueError:
            branch_id = None
    metrics, trends, districts, top_customers, branch = get_manager_dashboard_data(branch_id)
    return render_template(
        "manager_dashboard.html",
        metrics=metrics,
        trends=trends,
        districts=districts,
        top_customers=top_customers,
        branch=branch,
    )


@app.route("/reports/distributed")
@login_required("manager", "admin")
def distributed_report():
    primary_counts, secondary_counts = get_distributed_counts()
    return render_template(
        "distributed_report.html",
        primary_counts=primary_counts,
        secondary_counts=secondary_counts,
    )


# --------------------------
# Error handlers
# --------------------------
@app.errorhandler(403)
def forbidden(_error):
    return render_template("error.html", code=403, message="You do not have permission to access this page."), 403


@app.errorhandler(404)
def not_found(_error):
    return render_template("error.html", code=404, message="The page you requested was not found."), 404


@app.errorhandler(500)
def internal_error(_error):
    return render_template("error.html", code=500, message="An internal server error occurred."), 500



if __name__ == "__main__":
    app.run(debug=True)
