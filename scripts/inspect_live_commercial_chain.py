import urllib.request
import urllib.error
import json
import os
import time

BASE_URL = "https://ozhzo-api.onrender.com/api/v1"

def http(method, endpoint, token=None, data=None):
    url = f"{BASE_URL}{endpoint}"
    body = json.dumps(data).encode() if data is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode()), None
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            parsed = json.loads(raw)
        except:
            parsed = raw
        return e.code, None, parsed
    except Exception as e:
        return 0, None, str(e)

# 1. Admin login
print("1. Logging in Super Admin...")
admin_email = os.getenv("SUPER_ADMIN_EMAIL", "admin@example.com")
admin_pwd = os.getenv("SUPER_ADMIN_PASSWORD", "")
st, res, err = http("POST", "/admin/auth/login", data={"email": admin_email, "password": admin_pwd})
assert st == 200, f"Admin login failed: {err}"
admin_token = res["data"]["access_token"]
print("Admin Token OK.")

# 2. Register/Login customer
print("2. Registering/Logging in Customer...")
customer_email = os.getenv("TEST_CUSTOMER_EMAIL", f"cust_{int(time.time())}@ozhzo.com")
customer_pw = os.getenv("TEST_CUSTOMER_PASSWORD", f"Cust_{int(time.time())}!Aa1")
st, res, err = http("POST", "/auth/register", data={
    "email": customer_email,
    "password": customer_pw,
    "full_name": "Test Customer",
    "phone_number": "+919876543210",
    "country_code": "+91"
})
if st != 200:
    st, res, err = http("POST", "/auth/login", data={
        "login_identifier": customer_email,
        "password": customer_pw
    })
assert st == 200, f"Customer auth failed: {err}"
cust_token = res["access_token"]
print("Customer Token OK.")

# 3. Check customer plans & prices
print("3. Fetching Customer Plans (/subscription/plans)...")
st, res, err = http("GET", "/subscription/plans", token=cust_token)
print(f"Status: {st}")
for p in res.get("data", res):
    print("Plan:", p.get("name"), "ID:", p.get("id"))
    for pr in p.get("prices", []):
        print("  Price:", pr.get("currency"), pr.get("country"), "list_price:", pr.get("list_price"))

# 4. Check coupons
print("4. Fetching Admin Coupons...")
st, res, err = http("GET", "/admin/coupons", token=admin_token)
for c in res["data"]:
    print("Coupon:", c["id"], c["code"], c["name"], c["coupon_type"], c["discount_value"], c["status"])
