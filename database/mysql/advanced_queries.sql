-- 1. Calculate water bills based on usage and rates
SELECT
    w.usage_id,
    c.account_number,
    c.first_name,
    c.last_name,
    w.usage_month,
    w.units_used,
    r.rate_tier,
    r.price_per_unit,
    r.fixed_charge,
    (w.units_used * r.price_per_unit) + r.fixed_charge AS calculated_bill
FROM water_usage w
JOIN customers c ON c.customer_id = w.customer_id
JOIN billing_rates r ON w.units_used BETWEEN r.min_units AND r.max_units;

-- 2. Outstanding balances by customer
SELECT * FROM vw_customer_outstanding_balances
ORDER BY total_outstanding DESC;

-- 3. Payment history
SELECT
    p.payment_id,
    c.account_number,
    c.first_name,
    c.last_name,
    p.amount_paid,
    p.payment_method,
    p.payment_reference,
    p.payment_date
FROM payments p
JOIN customers c ON c.customer_id = p.customer_id
ORDER BY p.payment_date DESC;

-- 4. Water usage pattern report by district
SELECT * FROM vw_district_usage_summary
ORDER BY total_units_used DESC;

-- 5. Unpaid or partial bills
SELECT
    b.bill_id,
    c.account_number,
    c.first_name,
    c.last_name,
    b.bill_month,
    b.amount_due,
    b.outstanding_amount,
    b.status,
    b.due_date
FROM bills b
JOIN customers c ON c.customer_id = b.customer_id
WHERE LOWER(b.status) IN ('unpaid', 'partially paid')
ORDER BY b.due_date ASC;
