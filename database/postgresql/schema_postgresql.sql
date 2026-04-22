CREATE TABLE IF NOT EXISTS branches (
    branch_id SERIAL PRIMARY KEY,
    branch_name VARCHAR(100) NOT NULL UNIQUE,
    district VARCHAR(100) NOT NULL,
    branch_manager_name VARCHAR(120),
    phone VARCHAR(30),
    email VARCHAR(120),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    full_name VARCHAR(150) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role VARCHAR(30) NOT NULL CHECK (role IN ('admin','manager','customer')),
    branch_id INT REFERENCES branches(branch_id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id SERIAL PRIMARY KEY,
    user_id INT UNIQUE REFERENCES users(user_id) ON DELETE SET NULL,
    branch_id INT REFERENCES branches(branch_id),
    account_number VARCHAR(50) NOT NULL UNIQUE,
    meter_number VARCHAR(50) NOT NULL UNIQUE,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    phone VARCHAR(30) NOT NULL,
    district VARCHAR(100) NOT NULL,
    address TEXT NOT NULL,
    customer_type VARCHAR(40) DEFAULT 'Domestic',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS billing_rates (
    rate_id SERIAL PRIMARY KEY,
    rate_tier VARCHAR(40) NOT NULL UNIQUE,
    min_units NUMERIC(10,2) NOT NULL,
    max_units NUMERIC(10,2) NOT NULL,
    price_per_unit NUMERIC(10,2) NOT NULL,
    fixed_charge NUMERIC(10,2) DEFAULT 0,
    effective_from DATE NOT NULL,
    active_status VARCHAR(20) DEFAULT 'Active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS water_usage (
    usage_id SERIAL PRIMARY KEY,
    customer_id INT NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    usage_month DATE NOT NULL,
    previous_reading NUMERIC(12,2) NOT NULL,
    current_reading NUMERIC(12,2) NOT NULL,
    units_used NUMERIC(12,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_usage_reading CHECK (current_reading >= previous_reading)
);

CREATE TABLE IF NOT EXISTS bills (
    bill_id SERIAL PRIMARY KEY,
    customer_id INT NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    usage_id INT UNIQUE REFERENCES water_usage(usage_id) ON DELETE SET NULL,
    rate_id INT REFERENCES billing_rates(rate_id),
    bill_month DATE NOT NULL,
    units_used NUMERIC(12,2) NOT NULL,
    amount_due NUMERIC(12,2) NOT NULL,
    outstanding_amount NUMERIC(12,2) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'Unpaid',
    due_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS payments (
    payment_id SERIAL PRIMARY KEY,
    bill_id INT NOT NULL REFERENCES bills(bill_id) ON DELETE CASCADE,
    customer_id INT NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    amount_paid NUMERIC(12,2) NOT NULL,
    payment_method VARCHAR(40) NOT NULL,
    payment_reference VARCHAR(100),
    payment_gateway VARCHAR(80),
    payment_status VARCHAR(30) DEFAULT 'Completed',
    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS notifications (
    notification_id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES customers(customer_id) ON DELETE CASCADE,
    bill_id INT REFERENCES bills(bill_id) ON DELETE CASCADE,
    channel VARCHAR(20) NOT NULL,
    subject VARCHAR(150) NOT NULL,
    message TEXT NOT NULL,
    sent_status VARCHAR(20) DEFAULT 'Pending',
    sent_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS leak_reports (
    report_id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES customers(customer_id) ON DELETE SET NULL,
    location VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    status VARCHAR(30) DEFAULT 'Pending',
    priority VARCHAR(20) DEFAULT 'Medium',
    reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS service_requests (
    request_id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES customers(customer_id) ON DELETE SET NULL,
    request_type VARCHAR(60) NOT NULL,
    description TEXT NOT NULL,
    status VARCHAR(30) DEFAULT 'Open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_logs (
    log_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id) ON DELETE SET NULL,
    action_name VARCHAR(120) NOT NULL,
    action_details TEXT,
    action_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
