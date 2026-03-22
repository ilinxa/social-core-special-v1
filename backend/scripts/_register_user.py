import json
import sys
import urllib.request

email = sys.argv[1] if len(sys.argv) > 1 else "e2e_verify_test@test.com"
username = sys.argv[2] if len(sys.argv) > 2 else "e2e_verify_test"
password = "TestPass123!"

data = json.dumps(
    {
        "email": email,
        "password": password,
        "confirm_password": password,
        "username": username,
    }
).encode("utf-8")

req = urllib.request.Request(
    "http://localhost:8000/api/v1/auth/register/",
    data=data,
    headers={
        "Content-Type": "application/json",
        "X-Client-Type": "mobile",
    },
    method="POST",
)

try:
    with urllib.request.urlopen(req) as resp:
        body = json.loads(resp.read())
        print(f"OK email={body.get('email', '')} username={body.get('username', '')}")
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8")
    print(f"ERROR status={e.code} body={body}")
