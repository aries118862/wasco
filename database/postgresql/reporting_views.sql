CREATE OR REPLACE VIEW vw_customer_outstanding_balances AS
SELECT
    c.customer_id,
    c.account_number,
    c.first_name,
    c.last_name,
    c.district,
    COALESCE(SUM(b.amount_due),0) AS total_billed,
    COALESCE(SUM(p.amount_paid),0) AS total_paid,
    COALESCE(SUM(b.outstanding_amount),0) AS total_outstanding
FROM customers c
LEFT JOIN bills b ON b.customer_id = c.customer_id
LEFT JOIN payments p ON p.customer_id = c.customer_id
GROUP BY c.customer_id, c.account_number, c.first_name, c.last_name, c.district;

CREATE OR REPLACE VIEW vw_district_usage_summary AS
SELECT
    c.district,
    COUNT(DISTINCT c.customer_id) AS total_customers,
    COALESCE(SUM(w.units_used),0) AS total_units_used,
    COALESCE(SUM(b.amount_due),0) AS total_amount_billed
FROM customers c
LEFT JOIN water_usage w ON w.customer_id = c.customer_id
LEFT JOIN bills b ON b.customer_id = c.customer_id
GROUP BY c.district;
