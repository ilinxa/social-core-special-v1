import os
import sys

import psycopg2

email = sys.argv[1] if len(sys.argv) > 1 else "e2e_fresh@test.com"
conn = psycopg2.connect(
    dbname=os.getenv("POSTGRES_DB", "backend_core_db"),
    user=os.getenv("POSTGRES_USER", "django_user"),
    password=os.getenv("POSTGRES_PASSWORD", "postgres_dev_password"),
    host=os.getenv("POSTGRES_HOST", "localhost"),
    port=int(os.getenv("POSTGRES_PORT", "5432")),
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
