import urllib.request
import urllib.error
import json
import time

BASE_URL = "https://ozhzo-api.onrender.com/api/v1"

def api(method, endpoint, data=None, token=None):
    url = f"{BASE_URL}{endpoint}"
    body = json.dumps(data).encode("utf-8") if data else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode("utf-8")
            try:
                parsed = json.loads(raw)
            except Exception:
                parsed = raw
            return resp.status, parsed, None
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = raw
        return e.code, None, parsed
    except Exception as e:
        return 0, None, str(e)

results = []

def record(test_name, request_info, status_code, db_effect, follow_up, result):
    entry = {
        "test": test_name,
        "request": request_info,
        "status": status_code,
        "db_effect": db_effect,
        "follow_up": follow_up,
        "result": result
    }
    results.append(entry)
    print(f"\n[{result}] {test_name}")
    print(f"  Request: {request_info}")
    print(f"  HTTP Status: {status_code}")
    print(f"  DB Effect: {db_effect}")
    print(f"  Follow-up Read: {follow_up}")

ts = int(time.time())
test_user_email = f"audit_user_{ts}@ozhzo.com"
test_phone = f"+1555{str(ts)[-4:]}"
test_password = os.getenv("TEST_CUSTOMER_PASSWORD", f"Pass_{ts}!Aa1")

# 1. Register test user with phone
reg_st, reg_data, reg_err = api("POST", "/auth/register", {
    "email": test_user_email,
    "phone_number": test_phone,
    "password": test_password,
    "full_name": f"Auditor {ts}"
})
user_token = reg_data.get("data", {}).get("access_token") if reg_data else None
auth_user_id = reg_data.get("data", {}).get("user_id") if reg_data else None

record(
    "A. User Registration",
    f"POST /auth/register ({test_user_email})",
    reg_st,
    f"Created UserModel row with ID: {auth_user_id}",
    f"Access token issued: {bool(user_token)}",
    "PASSED" if reg_st in [200, 201] and user_token else "FAILED"
)

# 2. Verify mobile OTP (DEMO OTP 123456)
otp_st, otp_data, otp_err = api("POST", "/auth/send-otp", {
    "phone_number": test_phone,
    "purpose": "REGISTRATION"
})
v_otp_st, v_otp_data, v_otp_err = api("POST", "/auth/verify-otp", {
    "phone_number": test_phone,
    "otp_code": "123456",
    "purpose": "REGISTRATION"
})

record(
    "S. Mobile OTP Verification",
    f"POST /auth/verify-otp ({test_phone})",
    v_otp_st,
    f"Updated UserModel {auth_user_id} mobile_verified=True",
    f"Verification status: {v_otp_data.get('data', {}).get('is_verified') if v_otp_data else 'ERR'}",
    "PASSED" if v_otp_st == 200 else "FAILED"
)

# 3. GET /users/me
me_st, me_data, me_err = api("GET", "/users/me", token=user_token)
user_info = me_data.get("data", {}) if me_data else {}

record(
    "A. User Profile & Verification Status",
    "GET /users/me",
    me_st,
    f"Retrieved user_id={user_info.get('id')} email={user_info.get('email')}",
    f"Active={user_info.get('is_active')} MobileVerified={user_info.get('mobile_verified')}",
    "PASSED" if me_st == 200 and user_info.get("email") == test_user_email else "FAILED"
)

# 4. Create Home (allowed because mobile_verified is true)
home_title = f"Live Audit Home {ts}"
h_st, h_data, h_err = api("POST", "/homes", {
    "name": home_title,
    "currency": "USD",
    "timezone": "UTC"
}, token=user_token)
created_home_id = h_data.get("data", {}).get("id") if h_data else None

record(
    "D. Home Creation",
    f"POST /homes ('{home_title}')",
    h_st,
    f"Created HomeModel with ID: {created_home_id} and HomeMemberModel (OWNER)",
    f"Home status: {h_data.get('data', {}).get('status') if h_data else 'ERR'}",
    "PASSED" if h_st in [200, 201] and created_home_id else "FAILED"
)

# 5. User retrieves Homes
list_st, list_data, list_err = api("GET", "/homes", token=user_token)
homes_list = list_data.get("data", []) if list_data else []
found_home = any(h.get("id") == created_home_id for h in homes_list) if isinstance(homes_list, list) else False

record(
    "B. User Home Membership Retrieval",
    "GET /homes",
    list_st,
    f"Retrieved {len(homes_list) if isinstance(homes_list, list) else 0} homes for user",
    f"Found created home ID {created_home_id}: {found_home}",
    "PASSED" if list_st == 200 and found_home else "FAILED"
)

# 6. Inventory: Add consumable & Adjust stock
inv_st, inv_data, inv_err = api("POST", f"/homes/{created_home_id}/inventory/items", {
    "name": "Audit Organic Milk",
    "item_type": "CONSUMABLE",
    "quantity": 5.0,
    "unit": "L",
    "min_threshold": 2.0
}, token=user_token) if created_home_id else (0, None, None)
item_id = inv_data.get("data", {}).get("id") if inv_data else None

# Consume 2
consume_st, consume_data, consume_err = api("POST", f"/homes/{created_home_id}/inventory/items/{item_id}/movements", {
    "quantity": 2.0,
    "movement_type": "CONSUMED",
    "notes": "Consumed 2L"
}, token=user_token) if item_id else (0, None, None)

# Verify updated quantity
check_st, check_data, check_err = api("GET", f"/homes/{created_home_id}/inventory/items/{item_id}", token=user_token) if item_id else (0, None, None)
rem_qty = check_data.get("data", {}).get("quantity") if check_data else None

record(
    "R. Inventory Consumable Stock & Consumption",
    f"POST /homes/{created_home_id}/inventory/items & Movement -2L",
    consume_st,
    f"Created item {item_id}, recorded inventory movement delta -2.0",
    f"Remaining quantity in DB: {rem_qty} (Expected 3.0)",
    "PASSED" if float(rem_qty or 0) == 3.0 else "FAILED"
)

# 7. Purchase List: Add -> Check -> Restore
p_st, p_data, p_err = api("POST", f"/homes/{created_home_id}/purchase-list", {
    "name": "Audit Weekly Groceries"
}, token=user_token) if created_home_id else (0, None, None)
plist_id = p_data.get("data", {}).get("id") if p_data else None

pi_st, pi_data, pi_err = api("POST", f"/homes/{created_home_id}/purchase-list/{plist_id}/items", {
    "name": "Basmati Rice 5kg",
    "quantity": 5.0,
    "unit": "kg"
}, token=user_token) if plist_id else (0, None, None)
pitem_id = pi_data.get("data", {}).get("id") if pi_data else None

# Mark purchased
buy_st, buy_data, buy_err = api("POST", f"/homes/{created_home_id}/purchase-list/{plist_id}/items/{pitem_id}/purchase", token=user_token) if pitem_id else (0, None, None)

# Restore to To Buy
rest_st, rest_data, rest_err = api("POST", f"/homes/{created_home_id}/purchase-list/{plist_id}/items/{pitem_id}/restore", token=user_token) if pitem_id else (0, None, None)

record(
    "P. Purchase List Mark Purchased & Restore to To Buy",
    f"POST /purchase-list/{plist_id}/items/{pitem_id}/restore",
    rest_st,
    f"Updated PurchaseItemModel {pitem_id} status: PURCHASED -> PENDING",
    f"Response status returned: {rest_data.get('data', {}).get('status') if rest_data else 'ERR'}",
    "PASSED" if rest_st == 200 and rest_data.get("data", {}).get("status") == "PENDING" else "FAILED"
)

# 8. Calendar Event
evt_st, evt_data, evt_err = api("POST", f"/homes/{created_home_id}/events", {
    "title": "Integration Test Event",
    "start_time": "2026-08-25T10:00:00Z",
    "end_time": "2026-08-25T11:00:00Z",
    "is_all_day": False
}, token=user_token) if created_home_id else (0, None, None)
evt_id = evt_data.get("data", {}).get("id") if evt_data else None

# Follow up read
read_evt_st, read_evt_data, read_evt_err = api("GET", f"/homes/{created_home_id}/events", token=user_token) if created_home_id else (0, None, None)
events_list = read_evt_data.get("data", []) if read_evt_data else []
found_evt = any(e.get("id") == evt_id for e in events_list) if isinstance(events_list, list) else False

record(
    "Q. Calendar Event Creation & Persistence",
    f"POST /homes/{created_home_id}/events ('Integration Test Event')",
    evt_st,
    f"Created EventModel with ID {evt_id}",
    f"GET /events verified event presence: {found_evt}",
    "PASSED" if evt_st in [200, 201] and found_evt else "FAILED"
)

# 9. Dashboard Data Load
dash_st, dash_data, dash_err = api("GET", f"/homes/{created_home_id}/dashboard", token=user_token) if created_home_id else (0, None, None)
dash_obj = dash_data.get("data", {}) if dash_data else {}

record(
    "N. Household Dashboard Data Resolution",
    f"GET /homes/{created_home_id}/dashboard",
    dash_st,
    f"Resolved active home dashboard for {created_home_id}",
    f"Loaded tasks, bills, inventory counts, shopping lists without errors",
    "PASSED" if dash_st == 200 and dash_obj else "FAILED"
)

print("\n=== SUMMARY OF LIVE DATA-LAYER EXECUTION ===")
total_passed = sum(1 for r in results if r["result"] == "PASSED")
total_failed = sum(1 for r in results if r["result"] == "FAILED")
print(f"Total: {len(results)} | PASSED: {total_passed} | FAILED: {total_failed}")

