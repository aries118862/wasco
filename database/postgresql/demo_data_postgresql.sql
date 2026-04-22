INSERT INTO branches (branch_name, district, branch_manager_name, phone, email) VALUES
('Maseru Central', 'Maseru', 'Mpho Manager', '58000001', 'maseru@wasco.co.ls'),
('Leribe North', 'Leribe', 'Thabo Manager', '58000002', 'leribe@wasco.co.ls'),
('Mafeteng South', 'Mafeteng', 'Lerato Manager', '58000003', 'mafeteng@wasco.co.ls');

INSERT INTO users (full_name, email, password_hash, role, branch_id) VALUES
('System Administrator', 'admin@wasco.co.ls', 'scrypt:32768:8:1$05gMH81P5f7Wvce3$bf5294876f1d8fc4b5ab43e440ff2f8efaf7c1ceb664e01831bb52d8daa7c7155d21f95be89334adaf216c2de303ed2f9d07c9122549f1e90abf556c24aefb21', 'admin', 1),
('Maseru Branch Manager', 'manager@wasco.co.ls', 'scrypt:32768:8:1$neRj5uxV0RTZOXMB$576c8a5f24ae7521a8d8815962ae9aa73644c4c99d8957f7d535cff33d2a1eda310e5e971083503439a5e5c9ca9e510a816e2d000a1a7b926fdeba2e9fdd204c', 'manager', 1),
('Kabelo Selomo', 'kabelo@example.com', 'scrypt:32768:8:1$emj8YbpdBf5PrAIO$3f6cd19fa827690faa2404acd486939fb476c339280e344b9fc24e2ea1f9b54fc60cb26756be65c408fb58645d47efebdd1ba7bea61e074323745cd2dbd96788', 'customer', 1),
('Pontsho Motsoasele', 'pontsho@example.com', 'scrypt:32768:8:1$K7MV7Q8i5rHbsQey$59e571fadae9d328accdd87385862c07e917fcbfe87179d282da4f29809c71e63adb7a45a13b4f3f213986fe78539245588f8bbc8021fee1c4688e17aaa15f34', 'customer', 2);

INSERT INTO customers (user_id, branch_id, account_number, meter_number, first_name, last_name, email, phone, district, address, customer_type) VALUES
(3, 1, 'ACC-1001', 'MTR-2001', 'Kabelo', 'Selomo', 'kabelo@example.com', '62000001', 'Maseru', 'Ha Abia, Maseru', 'Domestic'),
(4, 2, 'ACC-1002', 'MTR-2002', 'Pontsho', 'Motsoasele', 'pontsho@example.com', '62000002', 'Leribe', 'Hlotse, Leribe', 'Domestic');

INSERT INTO billing_rates (rate_tier, min_units, max_units, price_per_unit, fixed_charge, effective_from, active_status) VALUES
('Tier 1', 0, 10, 8.00, 25.00, '2026-01-01', 'Active'),
('Tier 2', 10.01, 30, 11.50, 25.00, '2026-01-01', 'Active'),
('Tier 3', 30.01, 100000, 15.00, 25.00, '2026-01-01', 'Active');

INSERT INTO water_usage (customer_id, usage_month, previous_reading, current_reading, units_used) VALUES
(1, '2026-03-01', 1200, 1218, 18),
(2, '2026-03-01', 2300, 2338, 38),
(1, '2026-04-01', 1218, 1231, 13);

INSERT INTO bills (customer_id, usage_id, rate_id, bill_month, units_used, amount_due, outstanding_amount, status, due_date) VALUES
(1, 1, 2, '2026-03-01', 18, 232.00, 232.00, 'Unpaid', '2026-03-25'),
(2, 2, 3, '2026-03-01', 38, 595.00, 195.00, 'Partially Paid', '2026-03-25'),
(1, 3, 2, '2026-04-01', 13, 174.50, 0.00, 'Paid', '2026-04-25');

INSERT INTO payments (bill_id, customer_id, amount_paid, payment_method, payment_reference, payment_gateway, payment_status) VALUES
(2, 2, 400.00, 'Mpesa', 'PAY-3001', 'SandboxGateway', 'Completed'),
(3, 1, 174.50, 'Card', 'PAY-3002', 'SandboxGateway', 'Completed');

INSERT INTO notifications (customer_id, bill_id, channel, subject, message, sent_status, sent_at) VALUES
(1, 1, 'Email', 'New Water Bill', 'Your March bill has been generated.', 'Sent', CURRENT_TIMESTAMP),
(2, 2, 'SMS', 'Payment Reminder', 'You still have an outstanding balance.', 'Sent', CURRENT_TIMESTAMP);

INSERT INTO leak_reports (customer_id, location, description, status, priority) VALUES
(1, 'Ha Abia Main Road', 'Pipe leakage near roadside connection.', 'Pending', 'High'),
(2, 'Hlotse Market Area', 'Continuous leak close to communal tap.', 'In Progress', 'Medium');

INSERT INTO service_requests (customer_id, request_type, description, status) VALUES
(1, 'Meter Inspection', 'Please inspect possible over-reading on my meter.', 'Open'),
(2, 'Account Update', 'Need to update account contact details.', 'Closed');

INSERT INTO audit_logs (user_id, action_name, action_details) VALUES
(1, 'CREATE_RATE', 'Inserted 2026 water billing rates'),
(1, 'GENERATE_BILL', 'Generated bill for usage_id 1');
