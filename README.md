# WASCO Distributed Online Water Billing Database Application

## What this package includes
- Professional Flask web application with consistent WASCO-style interface
- Public homepage, services, bill enquiry, leak reporting and branch directory
- Secure role-based login for customers, administrators and branch managers
- Customer portal, administrative control panel and branch manager analytics dashboard
- PostgreSQL primary schema and MySQL secondary schema for heterogeneous database distribution
- Automatic synchronization from PostgreSQL to MySQL for key operational records
- Billing rate configuration, water usage capture, automatic bill generation and payment recording
- Chart.js analytics with usage trends, payment summaries, billing status charts and district comparisons
- Font Awesome online icons embedded through CDN for a polished dashboard experience
- Distributed database report comparing PostgreSQL and MySQL record counts

## Default local databases
- PostgreSQL database: `wasco`
- MySQL database: `wasco`

## Environment configuration
Create a `.env` file from `.env.example` and add your local or hosted database credentials.

```bash
pip install -r requirements.txt
cp .env.example .env
python app.py
```

## Seed login accounts
These accounts are provided in the seed data files or can be inserted manually.
- Admin: `admin@wasco.co.ls` / `admin123`
- Manager: `manager@wasco.co.ls` / `manager123`
- Customer: `kabelo@example.com` / `customer123`

## Payment integration note
The platform includes online-checkout initiation, callback handling and payment recording. For live production payments, add merchant credentials from the chosen payment provider and connect the gateway request logic in the `PaymentGateway` class inside `app.py`.
