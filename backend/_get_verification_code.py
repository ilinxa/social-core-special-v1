import sys
import psycopg2

email = sys.argv[1] if len(sys.argv) > 1 else "e2e_fresh@test.com"
conn = psycopg2.connect(
    dbname="backend_core_db",
    user="django_user",
    password="postgres_dev_password",
    host="localhost",
    port=5432,
)
cur = conn.cursor()
cur.execute(
    """
    SELECT code FROM auth_verification_tokens
    WHERE email = %s AND is_used = FALSE
    ORDER BY created_at DESC LIMIT 1
""",
    (email,),
)
row = cur.fetchone()
print(f"CODE={row[0]}") if row else print("NO_CODE")
conn.close()
