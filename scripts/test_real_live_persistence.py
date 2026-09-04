import urllib.request
import urllib.error
import json
import time

BASE_URL = "https://ozhzo-api.onrender.com/api/v1"

def login_super_admin():
    admin_email = os.getenv("SUPER_ADMIN_EMAIL", "admin@example.com")
    admin_pwd = os.getenv("SUPER_ADMIN_PASSWORD", "")
    req = urllib.request.Request(
        f"{BASE_URL}/admin/auth/login",
        data=json.dumps({"email": admin_email, "password": admin_pwd}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        return data["data"]["access_token"]

def api(method, endpoint, token, data=None):
    url = f"{BASE_URL}{endpoint}"
    body = json.dumps(data).encode() if data is not None else None
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw), None
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            parsed = json.loads(raw)
        except:
            parsed = raw
        return e.code, None, parsed
    except Exception as e:
        return 0, None, str(e)

print("=== 1. AUTHENTICATING SUPER ADMIN ===")
token = login_super_admin()
print("Token acquired:", token[:25] + "...")

# ------------------------------------------------------------------------------
# TEST A: Plan Edit Persistence
# ------------------------------------------------------------------------------
print("\n=== TEST A: PLAN EDIT & PERSISTENCE ===")
st, plans_res, err = api("GET", "/admin/subscriptions/plans", token)
assert st == 200 and plans_res["success"], f"Failed to get plans: {err}"
plan = plans_res["data"][0]
plan_id = plan["id"]
orig_name = plan["name"]
orig_desc = plan.get("description", "")
orig_max_homes = plan.get("max_homes", 5)
print(f"Original Plan: ID={plan_id}, Name='{orig_name}', max_homes={orig_max_homes}")

# Update Plan via PATCH
new_name = f"Ozhzo Home Premium {int(time.time())}"
new_desc = "Updated enterprise digital operating system."
new_max_homes = 10

print(f"Updating plan to Name='{new_name}', max_homes={new_max_homes}...")
st, update_res, err = api("PATCH", f"/admin/subscriptions/plans/{plan_id}", token, {
    "name": new_name,
    "description": new_desc,
    "max_homes": new_max_homes
})
print(f"Update response: status={st}, success={update_res.get('success') if update_res else False}")
if err:
    print(f"ERROR: {err}")

# Read back plan to verify persistence
st, verify_res, err = api("GET", "/admin/subscriptions/plans", token)
updated_plan = next((p for p in verify_res["data"] if p["id"] == plan_id), None)
print(f"Verified Plan: Name='{updated_plan['name']}', max_homes={updated_plan.get('max_homes')}")
assert updated_plan["name"] == new_name, "Plan name was not updated in DB!"

# Restore original plan name
api("PATCH", f"/admin/subscriptions/plans/{plan_id}", token, {
    "name": orig_name,
    "description": orig_desc,
    "max_homes": orig_max_homes
})
print(f"Restored plan name to '{orig_name}'.")

# ------------------------------------------------------------------------------
# TEST B: Regional Price Version Edit & Creation Persistence
# ------------------------------------------------------------------------------
print("\n=== TEST B: REGIONAL PRICING EDIT & PERSISTENCE ===")
st, prices_res, err = api("GET", "/admin/subscriptions/prices", token)
assert st == 200, f"Failed to get prices: {err}"
prices = prices_res["data"]
in_price = next((p for p in prices if p.get("country") == "IN"), None)
print(f"Current India (IN) Price: {in_price}")

if in_price:
    price_id = in_price["id"]
    orig_list_price = in_price["list_price"]
    # Update price via PATCH
    test_new_price = 2499.00
    print(f"Updating IN price from {orig_list_price} to {test_new_price}...")
    st, edit_price_res, err = api("PATCH", f"/admin/subscriptions/prices/{price_id}", token, {
        "list_price": test_new_price,
        "reason": "Annual inflation adjustment"
    })
    print(f"Price update status: {st}, res={edit_price_res}")
    if err:
        print(f"ERROR: {err}")

    # Verify persistence
    st, verify_prices_res, _ = api("GET", "/admin/subscriptions/prices", token)
    verified_in_price = next((p for p in verify_prices_res["data"] if p["id"] == price_id), None)
    print(f"Verified IN Price: {verified_in_price['list_price']}")
    
    # Restore original price
    api("PATCH", f"/admin/subscriptions/prices/{price_id}", token, {
        "list_price": orig_list_price,
        "reason": "Restored test value"
    })
    print(f"Restored IN Price to {orig_list_price}.")

# ------------------------------------------------------------------------------
# TEST C: Coupon Edit & Persistence
# ------------------------------------------------------------------------------
print("\n=== TEST C: COUPON EDIT & PERSISTENCE ===")
st, coupons_res, err = api("GET", "/admin/coupons", token)
assert st == 200, f"Failed to get coupons: {err}"
coupons = coupons_res["data"]
print(f"Available coupons count: {len(coupons)}")
for c in coupons:
    print(f"  Coupon: Code={c['code']}, Name='{c['name']}', Discount={c.get('discount_value')}, Status={c.get('status')}")

# Pick first coupon or create one
target_coupon = coupons[0]
c_id = target_coupon["id"]
orig_c_name = target_coupon["name"]
orig_discount = target_coupon.get("discount_value", 0)

new_c_name = f"Edited Coupon {int(time.time())}"
new_discount = 60.00
print(f"\nEditing Coupon {target_coupon['code']} (ID={c_id}) -> Name='{new_c_name}', discount={new_discount}...")
st, edit_c_res, err = api("PATCH", f"/admin/coupons/{c_id}", token, {
    "name": new_c_name,
    "discount_value": new_discount,
    "reason": "Commercial update Q4"
})
print(f"Coupon edit status: {st}, res={edit_c_res}")
if err:
    print(f"ERROR: {err}")

# Verify persistence
st, verify_c_res, _ = api("GET", "/admin/coupons", token)
verified_coupon = next((c for c in verify_c_res["data"] if c["id"] == c_id), None)
print(f"Verified Coupon from DB: Name='{verified_coupon['name']}', discount={verified_coupon.get('discount_value')}")

# Restore original coupon
api("PATCH", f"/admin/coupons/{c_id}", token, {
    "name": orig_c_name,
    "discount_value": orig_discount
})
print("Restored original coupon values.")

print("\n=== ALL LIVE PERSISTENCE CHECKS COMPLETED ===")
