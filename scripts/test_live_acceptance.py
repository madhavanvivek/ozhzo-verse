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

print("=== 1. TEST LOGIN CANDIDATES FOR VIVEK@ZINFOG.COM ===")
passwords = ["Caseno@123", "AdminPassword123!", "Password123!", "Vivek@123", "OzHzo@2026"]
for p in passwords:
    res = api_request("POST", "/auth/login", {"email": "vivek@zinfog.com", "password": p})
    print(f"Password '{p}': status={res['status']}, err={res['error']}, data_present={res['data'] is not None}")

