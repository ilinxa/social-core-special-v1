import sys
import psycopg2
email = sys.argv[1] if len(sys.argv) > 1 else "e2e_user_a@test.com"
conn = psycopg2.connect(dbname="backend_core_db", user="django_user", password="postgres_dev_password", host="localhost", port=5432)
cur = conn.cursor()
cur.execute("""
    SELECT t.token FROM auth_password_reset_tokens t
    JOIN users u ON t.user_id = u.id
    WHERE u.email = %s AND t.is_used = false
    ORDER BY t.created_at DESC LIMIT 1
""", (email,))
row = cur.fetchone()
print(f"TOKEN={row[0]}") if row else print("NO_TOKEN")
conn.close()
