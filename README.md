# WASCO Distributed Online Water Billing Database Application

## What this package includes
- Real Flask web application with one professional theme across all pages
- Public homepage, services, bill enquiry, leak reporting, branch directory
- Secure role-based login from one users table
- Customer, Admin and Branch Manager dashboards
- MySQL and PostgreSQL schema files with matching tables
- Payment module that is live-flow ready through a gateway adapter and callback endpoint
- Distributed database visibility page comparing PostgreSQL and MySQL record counts

## Default local databases
- PostgreSQL database: `wasco`
- MySQL database: `wasco`

## Default credentials expected by the app
- PostgreSQL: `postgres` / `12345`
- MySQL: `root` / `123456`

## Install
```bash
pip install -r requirements.txt
cp .env.example .env
python app.py
```

## Demo login accounts
These must exist in your database demo data or be inserted manually.
- Admin: `admin@wasco.co.ls` / `admin123`
- Manager: `manager@wasco.co.ls` / `manager123`
- Customer: `kabelo@example.com` / `customer123`

## Important payment note
The platform includes a working online-checkout initiation flow, callback route and payment recording flow. To process real live card or wallet payments, add your gateway merchant credentials and map the gateway request to the `PaymentGateway` class in `app.py`.
