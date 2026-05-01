# Setup Guide

1. Create the `wasco` database in PostgreSQL and MySQL.
2. Run the matching schema file in each database.
3. Run the matching seed data file in each database.
4. Install Python dependencies with `pip install -r requirements.txt`.
5. Copy `.env.example` to `.env` and update credentials.
6. Start the Flask app with `python app.py`.

PostgreSQL is configured as the primary operational database. MySQL is configured as the secondary heterogeneous database for distributed reporting and synchronized copies/fragments of selected operational records.
