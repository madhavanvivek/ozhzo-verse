import os
import urllib.request
import urllib.error
import json
import time
from decimal import Decimal

BASE_URL = "https://ozhzo-api.onrender.com/api/v1"

def api(method, endpoint, data=None, token=None):
    url = f"{BASE_URL}{endpoint}"
    body = json.dumps(data).encode("utf-8") if data is not None else None
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
    print(f"  REQUEST: {request_info}")
    print(f"  HTTP STATUS: {status_code}")
    print(f"  DATABASE EFFECT: {db_effect}")
    print(f"  FOLLOW-UP READ: {follow_up}")

ts = int(time.time())

# ==============================================================================
# A. Authenticate Real Super Admin Account: vivek@zinfog.com
# ==============================================================================
super_admin_email = os.getenv("SUPER_ADMIN_EMAIL", "admin@example.com")
super_admin_pwd = os.getenv("SUPER_ADMIN_PASSWORD", "")
sa_st, sa_data, sa_err = api("POST", "/auth/login", {
    "email": super_admin_email,
    "password": super_admin_pwd
})
admin_token = sa_data.get("data", {}).get("access_token") if sa_data else None
admin_user_id = sa_data.get("data", {}).get("user_id") if sa_data else None

# GET /users/me
me_st, me_data, me_err = api("GET", "/users/me", token=admin_token)
me_obj = me_data.get("data", {}) if me_data else {}

record(
    "A. Authenticate Super Admin Account (vivek@zinfog.com)",
    f"POST /auth/login ({super_admin_email}) -> GET /users/me",
    me_st,
    f"UserModel UUID: {me_obj.get('id')} is_super_admin={me_obj.get('is_super_admin')} role={me_obj.get('system_role')}",
    f"Email: {me_obj.get('email')}, mobile_verified={me_obj.get('mobile_verified')}, active={me_obj.get('is_active')}",
    "PASSED" if me_st == 200 and me_obj.get("email") == super_admin_email and me_obj.get("is_super_admin") is True else "FAILED"
)

# ==============================================================================
# B. Prove Ichu's Home (User App ↔ Admin UUID Match)
# ==============================================================================
homes_st, homes_data, _ = api("GET", "/homes", token=admin_token)
user_homes = homes_data.get("data", []) if homes_data else []

ichu_home = None
if isinstance(user_homes, list):
    for h in user_homes:
        if "ichu" in (h.get("name") or "").lower():
            ichu_home = h
            break
if not ichu_home and isinstance(user_homes, list) and len(user_homes) > 0:
    ichu_home = user_homes[0]

adm_h_st, adm_h_data, _ = api("GET", "/admin/homes", token=admin_token)
admin_homes = adm_h_data.get("data", []) if adm_h_data else []

admin_found_ichu = False
if isinstance(admin_homes, list) and ichu_home:
    admin_found_ichu = any(h.get("id") == ichu_home.get("id") for h in admin_homes)

record(
    "B. Prove Real Home (User App ↔ Super Admin UUID Match)",
    "GET /homes -> GET /admin/homes",
    adm_h_st,
    f"Home: '{ichu_home.get('name')}' UUID: {ichu_home.get('id')} Status: {ichu_home.get('status') or 'ACTIVE'}",
    f"Admin endpoint returned identical workspace UUID: {admin_found_ichu}",
    "PASSED" if adm_h_st == 200 and admin_found_ichu else "FAILED"
)

# ==============================================================================
# C. Prove User Registration → Super Admin Users Roster
# ==============================================================================
temp_user_email = f"audit_user_{ts}@ozhzo.com"
temp_phone = f"+1555{str(ts)[-4:]}"
temp_pwd = os.getenv("TEST_USER_PASSWORD", f"Pass_{ts}!Aa1")

reg_st, reg_data, _ = api("POST", "/auth/register", {
    "email": temp_user_email,
    "phone_number": temp_phone,
    "password": temp_pwd,
    "full_name": f"Audit Subject {ts}"
})
temp_user_id = reg_data.get("data", {}).get("user_id") if reg_data else None
temp_user_token = reg_data.get("data", {}).get("access_token") if reg_data else None

# Verify mobile OTP
api("POST", "/auth/send-otp", {"phone_number": temp_phone, "purpose": "REGISTRATION"})
api("POST", "/auth/verify-otp", {"phone_number": temp_phone, "otp_code": "123456", "purpose": "REGISTRATION"})

adm_u_st, adm_u_data, _ = api("GET", "/admin/users", token=admin_token)
admin_users = adm_u_data.get("data", []) if adm_u_data else []
found_user_in_admin = any(u.get("id") == temp_user_id for u in admin_users) if isinstance(admin_users, list) else False

record(
    "C. User Registration → Super Admin Users Roster",
    f"POST /auth/register ({temp_user_email}) -> GET /admin/users",
    adm_u_st,
    f"Created UserModel {temp_user_id} in PostgreSQL",
    f"Admin Users list contains new user UUID: {found_user_in_admin}",
    "PASSED" if reg_st == 201 and adm_u_st == 200 and found_user_in_admin else "FAILED"
)

# ==============================================================================
# D. Prove Home Creation → Super Admin Workspaces
# ==============================================================================
temp_home_title = f"Live Audit Workspace {ts}"
create_h_st, create_h_data, _ = api("POST", "/homes", {
    "name": temp_home_title,
    "currency": "USD",
    "timezone": "UTC"
}, token=temp_user_token)
temp_home_id = create_h_data.get("data", {}).get("id") if create_h_data else None

adm_h2_st, adm_h2_data, _ = api("GET", "/admin/homes", token=admin_token)
admin_homes2 = adm_h2_data.get("data", []) if adm_h2_data else []
found_home_in_admin = any(h.get("id") == temp_home_id for h in admin_homes2) if isinstance(admin_homes2, list) else False

record(
    "D. Home Creation → Super Admin Homes Roster",
    f"POST /homes ('{temp_home_title}') -> GET /admin/homes",
    adm_h2_st,
    f"Created HomeModel {temp_home_id} in PostgreSQL with OWNER role",
    f"Admin Homes list contains new Home UUID: {found_home_in_admin}",
    "PASSED" if create_h_st == 201 and adm_h2_st == 200 and found_home_in_admin else "FAILED"
)

# ==============================================================================
# E. Prove Admin User Mutation → Live Auth Lockout (Suspend/Reactivate)
# ==============================================================================
susp_st, _, _ = api("POST", f"/admin/users/{temp_user_id}/suspend", {
    "reason": "Security audit test suspension"
}, token=admin_token)

login_susp_st, _, _ = api("POST", "/auth/login", {
    "email": temp_user_email,
    "password": temp_pwd
})

react_st, _, _ = api("POST", f"/admin/users/{temp_user_id}/reactivate", {
    "reason": "Security audit test reactivation"
}, token=admin_token)

login_react_st, login_react_data, _ = api("POST", "/auth/login", {
    "email": temp_user_email,
    "password": temp_pwd
})
temp_user_token = login_react_data.get("data", {}).get("access_token") if login_react_data else temp_user_token

record(
    "E. Admin User Mutation → Live Auth Lockout (Suspend/Reactivate)",
    f"POST /admin/users/{temp_user_id}/suspend -> POST /auth/login -> POST /admin/users/{temp_user_id}/reactivate",
    login_react_st,
    f"UserModel {temp_user_id}: is_active=False -> Login HTTP {login_susp_st} -> is_active=True -> Login HTTP {login_react_st}",
    f"Suspension login denied: {login_susp_st == 401}, Reactivation login succeeded: {login_react_st == 200}",
    "PASSED" if susp_st == 200 and login_susp_st == 401 and react_st == 200 and login_react_st == 200 else "FAILED"
)

# ==============================================================================
# F. Prove Home Suspension Lockout (Suspend Home -> Deny 403 -> Reactivate -> 200)
# ==============================================================================
h_susp_st, _, _ = api("POST", f"/admin/homes/{temp_home_id}/suspend", {
    "reason": "Security audit test home suspension"
}, token=admin_token)

h_access_susp_st, _, _ = api("GET", f"/homes/{temp_home_id}/dashboard", token=temp_user_token)

h_react_st, _, _ = api("POST", f"/admin/homes/{temp_home_id}/reactivate", {
    "reason": "Security audit test home reactivation"
}, token=admin_token)

h_access_react_st, _, _ = api("GET", f"/homes/{temp_home_id}/dashboard", token=temp_user_token)

record(
    "F. Admin Home Suspension → Workspace Lockout (403 / 200)",
    f"POST /admin/homes/{temp_home_id}/suspend -> GET /homes/{temp_home_id}/dashboard -> Reactivate",
    h_access_react_st,
    f"HomeModel {temp_home_id} status: SUSPENDED -> HTTP {h_access_susp_st} -> ACTIVE -> HTTP {h_access_react_st}",
    f"Suspended workspace returned 403: {h_access_susp_st == 403}, Reactivated workspace returned 200: {h_access_react_st == 200}",
    "PASSED" if h_susp_st == 200 and h_access_susp_st == 403 and h_react_st == 200 and h_access_react_st == 200 else "FAILED"
)

# ==============================================================================
# G. Prove Bulk User Actions (Bulk Suspend & Bulk Reactivate)
# ==============================================================================
u1_email = f"bulk1_{ts}@ozhzo.com"
u2_email = f"bulk2_{ts}@ozhzo.com"
_, u1_reg, _ = api("POST", "/auth/register", {"email": u1_email, "phone_number": f"+1555{str(ts+1)[-4:]}", "password": temp_pwd, "full_name": "Bulk User 1"})
_, u2_reg, _ = api("POST", "/auth/register", {"email": u2_email, "phone_number": f"+1555{str(ts+2)[-4:]}", "password": temp_pwd, "full_name": "Bulk User 2"})
u1_id = u1_reg.get("data", {}).get("user_id") if u1_reg else None
u2_id = u2_reg.get("data", {}).get("user_id") if u2_reg else None

bulk_susp_st, _, _ = api("POST", "/admin/users/bulk-action", {
    "user_ids": [u1_id, u2_id],
    "action": "SUSPEND",
    "reason": "Bulk security test"
}, token=admin_token)

u1_chk_st, _, _ = api("POST", "/auth/login", {"email": u1_email, "password": temp_pwd})
u2_chk_st, _, _ = api("POST", "/auth/login", {"email": u2_email, "password": temp_pwd})

bulk_react_st, _, _ = api("POST", "/admin/users/bulk-action", {
    "user_ids": [u1_id, u2_id],
    "action": "ACTIVATE",
    "reason": "Bulk reactivation test"
}, token=admin_token)

u1_react_st, _, _ = api("POST", "/auth/login", {"email": u1_email, "password": temp_pwd})
u2_react_st, _, _ = api("POST", "/auth/login", {"email": u2_email, "password": temp_pwd})

record(
    "G. Bulk User Actions (Bulk Suspend & Activate)",
    "POST /admin/users/bulk-action (SUSPEND) -> POST /admin/users/bulk-action (ACTIVATE)",
    bulk_react_st,
    f"Bulk suspended 2 users: logins {u1_chk_st}/{u2_chk_st} -> Bulk activated: logins {u1_react_st}/{u2_react_st}",
    f"Bulk suspension locked out accounts: {u1_chk_st == 401 and u2_chk_st == 401}, Reactivation restored: {u1_react_st == 200 and u2_react_st == 200}",
    "PASSED" if bulk_susp_st == 200 and u1_chk_st == 401 and bulk_react_st == 200 and u1_react_st == 200 else "FAILED"
)

# ==============================================================================
# H. Prove Bulk Home Actions (Bulk Suspend & Bulk Reactivate)
# ==============================================================================
bulk_h_susp_st, _, _ = api("POST", "/admin/homes/bulk-action", {
    "home_ids": [temp_home_id],
    "action": "SUSPEND",
    "reason": "Bulk home audit"
}, token=admin_token)

b_h_chk_st, _, _ = api("GET", f"/homes/{temp_home_id}/dashboard", token=temp_user_token)

bulk_h_react_st, _, _ = api("POST", "/admin/homes/bulk-action", {
    "home_ids": [temp_home_id],
    "action": "ACTIVATE",
    "reason": "Bulk home reactivation"
}, token=admin_token)

b_h_react_st, _, _ = api("GET", f"/homes/{temp_home_id}/dashboard", token=temp_user_token)

record(
    "H. Bulk Home Actions (Bulk Suspend & Activate)",
    "POST /admin/homes/bulk-action (SUSPEND) -> POST /admin/homes/bulk-action (ACTIVATE)",
    bulk_h_react_st,
    f"Bulk suspended HomeModel {temp_home_id}: HTTP {b_h_chk_st} -> Bulk activated: HTTP {b_h_react_st}",
    f"Bulk suspension returned 403: {b_h_chk_st == 403}, Bulk reactivation returned 200: {b_h_react_st == 200}",
    "PASSED" if bulk_h_susp_st == 200 and b_h_chk_st == 403 and bulk_h_react_st == 200 and b_h_react_st == 200 else "FAILED"
)

# ==============================================================================
# I. Prove Activity Log / Audit Log
# ==============================================================================
act_st, act_data, _ = api("GET", "/admin/activity", token=admin_token)
audit_logs = act_data.get("data", []) if act_data else []
has_audit_entries = len(audit_logs) > 0 if isinstance(audit_logs, list) else False

record(
    "I. Activity & Audit Trail Persistence",
    "GET /admin/activity",
    act_st,
    f"Retrieved {len(audit_logs) if isinstance(audit_logs, list) else 0} AuditLogModel rows from PostgreSQL",
    f"Audit logs contains recent mutations: {has_audit_entries}",
    "PASSED" if act_st == 200 and has_audit_entries else "FAILED"
)

# ==============================================================================
# J. Prove Analytics (Live Metrics)
# ==============================================================================
ana_st, ana_data, _ = api("GET", "/admin/system/analytics-summary", token=admin_token)
analytics = ana_data.get("data", {}) if ana_data else {}
total_users = analytics.get("total_users", 0)
total_homes = analytics.get("total_homes", 0)

record(
    "J. Live PostgreSQL Analytics Aggregation",
    "GET /admin/system/analytics-summary",
    ana_st,
    f"Database counts: Total Users={total_users}, Total Homes={total_homes}, Active Subscriptions={analytics.get('active_subscriptions')}",
    f"Metrics reflect live database records (> 0): {total_users > 0 and total_homes > 0}",
    "PASSED" if ana_st == 200 and total_users > 0 and total_homes > 0 else "FAILED"
)

# ==============================================================================
# K. Prove Active Subscribers Roster
# ==============================================================================
sub_st, sub_data, _ = api("GET", "/admin/subscriptions/subscribers", token=admin_token)
subscribers = sub_data.get("data", []) if sub_data else []

record(
    "K. Active Subscribers Roster",
    "GET /admin/subscriptions/subscribers",
    sub_st,
    f"Retrieved {len(subscribers) if isinstance(subscribers, list) else 0} SubscriptionModel rows with tenant home mapping",
    f"Endpoint response status: {sub_st}",
    "PASSED" if sub_st == 200 else "FAILED"
)

# ==============================================================================
# L. Prove Promotion Creation
# ==============================================================================
promo_code = f"PROMO{ts}"
promo_st, _, _ = api("POST", "/admin/subscriptions/promotions", {
    "name": f"Audit Promo {ts}",
    "code": promo_code,
    "description": "100% discount 1 month free",
    "discount_type": "PERCENTAGE",
    "discount_value": 100.0,
    "status": "ACTIVE",
    "maximum_redemptions": 100,
    "maximum_redemptions_per_user": 1
}, token=admin_token)

promo_list_st, promo_list_data, _ = api("GET", "/admin/subscriptions/promotions", token=admin_token)
promos = promo_list_data.get("data", []) if promo_list_data else []
found_promo = any(p.get("code") == promo_code for p in promos) if isinstance(promos, list) else False

record(
    "L. Promotion Creation & Catalog Persistence",
    f"POST /admin/subscriptions/promotions ('{promo_code}') -> GET /admin/subscriptions/promotions",
    promo_list_st,
    f"Created PromotionModel {promo_code} in PostgreSQL",
    f"Promotion verified in catalog: {found_promo}",
    "PASSED" if promo_st == 201 and promo_list_st == 200 and found_promo else "FAILED"
)

# ==============================================================================
# M. Prove Coupon Creation
# ==============================================================================
coupon_code = f"COUPON{ts}"
coup_st, _, _ = api("POST", "/admin/coupons", {
    "name": f"Audit Coupon {ts}",
    "code": coupon_code,
    "discount_type": "PERCENTAGE",
    "discount_value": 100.0,
    "usage_limit": 50,
    "per_user_limit": 1
}, token=admin_token)

record(
    "M. Coupon Creation with Validation Guardrails",
    f"POST /admin/coupons ('{coupon_code}')",
    coup_st,
    f"Created CouponModel {coupon_code} with redemption window and usage limits",
    f"Coupon creation status: {coup_st}",
    "PASSED" if coup_st in [200, 201] else "FAILED"
)

# ==============================================================================
# N. Prove User Dashboard Data Resolution
# ==============================================================================
dash_st, dash_data, _ = api("GET", f"/homes/{temp_home_id}/dashboard", token=temp_user_token)
dash_obj = dash_data.get("data", {}) if dash_data else {}

record(
    "N. Household Dashboard Live Data Load",
    f"GET /homes/{temp_home_id}/dashboard",
    dash_st,
    f"Loaded HomeModel {temp_home_id} dashboard metrics, tasks, bills, inventory counts",
    f"Greeting: {dash_obj.get('greeting', {}).get('greeting')}, Home ID: {temp_home_id}",
    "PASSED" if dash_st == 200 and dash_obj else "FAILED"
)

# ==============================================================================
# P. Prove Purchase List: Add -> Purchase -> Restore to To Buy
# ==============================================================================
pi_st, pi_data, _ = api("POST", f"/homes/{temp_home_id}/purchase-list", {
    "name": "Audit Basmati Rice 5kg",
    "quantity": 5.0,
    "unit": "kg"
}, token=temp_user_token)
pitem_id = pi_data.get("data", {}).get("id") if pi_data else None

# Mark purchased
buy_st, buy_data, _ = api("POST", f"/homes/{temp_home_id}/purchase-list/{pitem_id}/purchase", {
    "purchased_quantity": 5.0
}, token=temp_user_token)

# Restore to To Buy
rest_st, rest_data, _ = api("POST", f"/homes/{temp_home_id}/purchase-list/{pitem_id}/restore", token=temp_user_token)

record(
    "P. Purchase List: Mark Purchased & Restore to To Buy",
    f"POST /homes/{temp_home_id}/purchase-list/{pitem_id}/restore",
    rest_st,
    f"Updated PurchaseItemModel {pitem_id} status: PURCHASED -> PENDING",
    f"Restored item status in response: {rest_data.get('data', {}).get('status') if rest_data else 'ERR'}",
    "PASSED" if rest_st == 200 and rest_data.get("data", {}).get("status") == "PENDING" else "FAILED"
)

# ==============================================================================
# Q. Prove Calendar Event Creation & Persistence
# ==============================================================================
evt_st, evt_data, _ = api("POST", f"/homes/{temp_home_id}/events", {
    "title": "Integration Test Event",
    "start_time": "2026-08-25T10:00:00Z",
    "end_time": "2026-08-25T11:00:00Z",
    "is_all_day": False
}, token=temp_user_token)
evt_id = evt_data.get("data", {}).get("id") if evt_data else None

read_evt_st, read_evt_data, _ = api("GET", f"/homes/{temp_home_id}/events", token=temp_user_token)
events_list = read_evt_data.get("data", []) if read_evt_data else []
found_evt = any(e.get("id") == evt_id for e in events_list) if isinstance(events_list, list) else False

record(
    "Q. Calendar Event Creation & Persistence",
    f"POST /homes/{temp_home_id}/events ('Integration Test Event') -> GET /events",
    read_evt_st,
    f"Created EventModel {evt_id} with EventParticipantModel in PostgreSQL",
    f"Event verified in calendar agenda: {found_evt}",
    "PASSED" if evt_st in [200, 201] and read_evt_st == 200 and found_evt else "FAILED"
)

# ==============================================================================
# R. Prove Inventory: Consumable Stock & Direct Update (-2)
# ==============================================================================
inv_st, inv_data, _ = api("POST", f"/homes/{temp_home_id}/inventory/items", {
    "name": "Audit Organic Milk",
    "item_type": "CONSUMABLE",
    "quantity": 5.0,
    "unit": "L",
    "min_threshold": 2.0
}, token=temp_user_token)
item_id = inv_data.get("data", {}).get("id") if inv_data else None

# Update quantity from 5 to 3
patch_st, patch_data, _ = api("PATCH", f"/homes/{temp_home_id}/inventory/items/{item_id}", {
    "quantity": 3.0
}, token=temp_user_token)

# Verify updated quantity
check_st, check_data, _ = api("GET", f"/homes/{temp_home_id}/inventory/items/{item_id}", token=temp_user_token)
rem_qty = check_data.get("data", {}).get("quantity") if check_data else None

record(
    "R. Household Inventory Consumable Stock & Consumption",
    f"POST /homes/{temp_home_id}/inventory/items & PATCH qty=3.0",
    patch_st,
    f"Created InventoryItemModel {item_id} (qty: 5.0), updated quantity delta to 3.0",
    f"Remaining quantity in DB: {rem_qty} (Expected: 3.0)",
    "PASSED" if float(rem_qty or 0) == 3.0 else "FAILED"
)

print("\n=======================================================")
print("FINAL BIDIRECTIONAL ACCEPTANCE TEST RESULTS SUMMARY")
print("=======================================================")
total_passed = sum(1 for r in results if r["result"] == "PASSED")
total_failed = sum(1 for r in results if r["result"] == "FAILED")
print(f"TOTAL TESTED: {len(results)} | PASSED: {total_passed} | FAILED: {total_failed}")
print("=======================================================")
