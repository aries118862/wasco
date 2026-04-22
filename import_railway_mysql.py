import pymysql

SQL_FILE = r"C:\Users\KABELO\Desktop\wasco_mysql.sql"

conn = pymysql.connect(
    host="roundhouse.proxy.rlwy.net",
    port=13237,
    user="root",
    password="qEdtAscCNEALiBwyvTIyNxkeEsArUeJO",
    database="railway",
    charset="utf8mb4",
    autocommit=False,
    ssl={"ssl": {}}
)

with open(SQL_FILE, "r", encoding="utf-8") as f:
    sql = f.read()

statements = [s.strip() for s in sql.split(";") if s.strip()]

try:
    with conn.cursor() as cursor:
        for stmt in statements:
            cursor.execute(stmt)
    conn.commit()
    print("Import completed successfully.")
except Exception as e:
    conn.rollback()
    print("Import failed:", e)
finally:
    conn.close()