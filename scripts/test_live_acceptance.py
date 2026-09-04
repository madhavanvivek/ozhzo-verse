import os
import urllib.request
import urllib.error
import json
import time

BASE_URL = "https://ozhzo-api.onrender.com/api/v1"

def api_request(method, endpoint, data=None, token=None):
    url = f"{BASE_URL}{endpoint}"
    body = json.dumps(data).encode("utf-8") if data else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            resp_body = resp.read().decode("utf-8")
            try:
                parsed = json.loads(resp_body)
            except Exception:
                parsed = resp_body
            return {"status": status, "data": parsed, "error": None}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        try:
            parsed = json.loads(err_body)
        except Exception:
            parsed = err_body
        return {"status": e.code, "data": None, "error": parsed}
    except Exception as e:
        return {"status": 0, "data": None, "error": str(e)}

print("=== 1. TEST LOGIN CANDIDATES ===")
target_email = os.getenv("SUPER_ADMIN_EMAIL", "admin@example.com")
passwords = [os.getenv("SUPER_ADMIN_PASSWORD", "")]
for p in passwords:
    if not p:
        continue
    res = api_request("POST", "/auth/login", {"email": target_email, "password": p})
    print(f"Candidate check: status={res['status']}, err={res['error']}, data_present={res['data'] is not None}")

