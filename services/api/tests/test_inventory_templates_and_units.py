import pytest
from decimal import Decimal
from httpx import AsyncClient, ASGITransport
from src.main import app


@pytest.mark.asyncio
async def test_inventory_templates_and_units_suite():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register Users (Super Admin, Home Owner A, Home Owner B)
        # Super Admin
        sa_res = await client.post("/api/v1/auth/register", json={
            "email": "superadmin_tpl@ozhzo.com",
            "password": "Password123!",
            "full_name": "Super Admin"
        })
        sa_token = sa_res.json()["data"]["tokens"]["access_token"]
        sa_headers = {"Authorization": f"Bearer {sa_token}"}

        # User A
        u_a = await client.post("/api/v1/auth/register", json={
            "email": "owner_a_tpl@ozhzo.com",
            "password": "Password123!",
            "full_name": "Madhavan Owner"
        })
        token_a = u_a.json()["data"]["tokens"]["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # User B
        u_b = await client.post("/api/v1/auth/register", json={
            "email": "owner_b_tpl@ozhzo.com",
            "password": "Password123!",
            "full_name": "Karthik Owner"
        })
        token_b = u_b.json()["data"]["tokens"]["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # Create Home A & Home B
        home_a_res = await client.post("/api/v1/homes", json={"name": "Madhavan Home"}, headers=headers_a)
        home_a_id = home_a_res.json()["data"]["id"]

        home_b_res = await client.post("/api/v1/homes", json={"name": "Karthik Home"}, headers=headers_b)
        home_b_id = home_b_res.json()["data"]["id"]

        # -------------------------------------------------------------
        # Test 1, 2, 3: Global Inventory Templates Catalog & Super Admin CRUD
        # -------------------------------------------------------------
        # List default templates (auto-seeded)
        tpl_list_res = await client.get("/api/v1/inventory/templates", headers=headers_a)
        assert tpl_list_res.status_code == 200
        templates = tpl_list_res.json()["data"]
        assert len(templates) >= 15
        rice_tpl = next(t for t in templates if t["name"] == "Rice")
        assert rice_tpl["default_unit"] == "kg"
        assert rice_tpl["default_category_name"] == "Pantry"

        # Super Admin creates custom global template
        create_tpl_res = await client.post("/api/v1/admin/inventory/templates", json={
            "name": "Olive Oil (Extra Virgin)",
            "default_category_name": "Pantry",
            "default_unit": "L",
            "description": "Cold pressed organic extra virgin olive oil",
            "sort_order": 50
        }, headers=sa_headers)
        assert create_tpl_res.status_code == 201
        custom_tpl_id = create_tpl_res.json()["data"]["id"]

        # Super Admin updates template
        update_tpl_res = await client.patch(f"/api/v1/admin/inventory/templates/{custom_tpl_id}", json={
            "description": "Updated cold pressed extra virgin olive oil"
        }, headers=sa_headers)
        assert update_tpl_res.status_code == 200
        assert update_tpl_res.json()["data"]["description"] == "Updated cold pressed extra virgin olive oil"

        # -------------------------------------------------------------
        # Test 16, 17, 18: Global and Home Custom Units Master
        # -------------------------------------------------------------
        # List available units in Home A (Global defaults seeded)
        units_res = await client.get(f"/api/v1/homes/{home_a_id}/units", headers=headers_a)
        assert units_res.status_code == 200
        units_list = units_res.json()["data"]
        assert any(u["symbol"] == "kg" for u in units_list)
        assert any(u["symbol"] == "L" for u in units_list)
        assert any(u["symbol"] == "pcs" for u in units_list)

        # Home A creates custom unit "bundle"
        custom_unit_res = await client.post(f"/api/v1/homes/{home_a_id}/units", json={
            "name": "Bundle",
            "symbol": "bundle",
            "measurement_type": "COUNT",
            "sort_order": 110
        }, headers=headers_a)
        assert custom_unit_res.status_code == 201
        custom_unit_id = custom_unit_res.json()["data"]["id"]
        assert custom_unit_res.json()["data"]["symbol"] == "bundle"
        assert custom_unit_res.json()["data"]["is_global"] is False

        # Deactivate unit (safeguard against destructive delete)
        deact_res = await client.delete(f"/api/v1/homes/{home_a_id}/units/{custom_unit_id}", headers=headers_a)
        assert deact_res.status_code == 200

        # Listing active units excludes deactivated
        units_active = await client.get(f"/api/v1/homes/{home_a_id}/units", headers=headers_a)
        assert not any(u["id"] == custom_unit_id for u in units_active.json()["data"])

        # Listing with include_inactive=True includes it
        units_all = await client.get(f"/api/v1/homes/{home_a_id}/units?include_inactive=true", headers=headers_a)
        assert any(u["id"] == custom_unit_id for u in units_all.json()["data"])

        # Reactivate unit
        react_res = await client.patch(f"/api/v1/homes/{home_a_id}/units/{custom_unit_id}", json={
            "is_active": True
        }, headers=headers_a)
        assert react_res.status_code == 200
        assert react_res.json()["data"]["is_active"] is True

        # -------------------------------------------------------------
        # Test 4-14: Home Selects Template, Customizes, Assigns Location Hierarchy
        # -------------------------------------------------------------
        # Create Hierarchical Locations in Home A: Kitchen > Pantry > 2nd Shelf > Blue Container
        kitchen_res = await client.post(f"/api/v1/homes/{home_a_id}/locations", json={
            "name": "Kitchen",
            "location_type": "ROOM"
        }, headers=headers_a)
        kitchen_id = kitchen_res.json()["data"]["id"]

        pantry_loc_res = await client.post(f"/api/v1/homes/{home_a_id}/locations", json={
            "name": "Pantry",
            "parent_id": kitchen_id,
            "location_type": "ZONE"
        }, headers=headers_a)
        pantry_loc_id = pantry_loc_res.json()["data"]["id"]

        shelf_res = await client.post(f"/api/v1/homes/{home_a_id}/locations", json={
            "name": "2nd Shelf",
            "parent_id": pantry_loc_id,
            "location_type": "SHELF"
        }, headers=headers_a)
        shelf_id = shelf_res.json()["data"]["id"]

        blue_container_res = await client.post(f"/api/v1/homes/{home_a_id}/locations", json={
            "name": "Blue Container",
            "parent_id": shelf_id,
            "location_type": "CONTAINER"
        }, headers=headers_a)
        blue_container_id = blue_container_res.json()["data"]["id"]

        # Create Category in Home A
        cat_res = await client.post(f"/api/v1/homes/{home_a_id}/inventory/categories", json={
            "name": "Pantry"
        }, headers=headers_a)
        cat_id = cat_res.json()["data"]["id"]

        # Home A selects "Rice" template and customizes: Basmati Rice, 3kg, min 5kg, pref 10kg, Blue Container
        item_create_res = await client.post(f"/api/v1/homes/{home_a_id}/inventory/items", json={
            "template_id": rice_tpl["id"],
            "name": "Basmati Rice",
            "category_id": cat_id,
            "location_id": blue_container_id,
            "quantity": 3.0,
            "unit": "kg",
            "min_threshold": 5.0,
            "preferred_quantity": 10.0,
            "notes": "Premium long grain"
        }, headers=headers_a)
        assert item_create_res.status_code == 201
        item_data = item_create_res.json()["data"]
        item_id = item_data["id"]
        assert item_data["name"] == "Basmati Rice"
        assert item_data["quantity"] == "3.000" or item_data["quantity"] == 3.0
        assert item_data["status"] == "LOW"
        assert item_data["location_path"] == "Kitchen > Pantry > 2nd Shelf > Blue Container"

        # -------------------------------------------------------------
        # Test 19: Global Template changes do NOT alter existing Home Items
        # -------------------------------------------------------------
        # Super Admin modifies Rice template default unit
        await client.patch(f"/api/v1/admin/inventory/templates/{rice_tpl['id']}", json={
            "default_unit": "packet"
        }, headers=sa_headers)

        # Home A's Basmati Rice remains "kg"
        item_get_res = await client.get(f"/api/v1/homes/{home_a_id}/inventory/items/{item_id}", headers=headers_a)
        assert item_get_res.status_code == 200
        assert item_get_res.json()["data"]["unit"] == "kg"
        assert item_get_res.json()["data"]["name"] == "Basmati Rice"

        # -------------------------------------------------------------
        # Test 15: Home creates custom item without global template
        # -------------------------------------------------------------
        custom_item_res = await client.post(f"/api/v1/homes/{home_a_id}/inventory/items", json={
            "name": "Grandma's Homemade Mango Pickle",
            "category_id": cat_id,
            "quantity": 1.0,
            "unit": "bottle",
            "min_threshold": 1.0,
            "notes": "Authentic spicy recipe"
        }, headers=headers_a)
        assert custom_item_res.status_code == 201
        assert custom_item_res.json()["data"]["template_id"] is None
        assert custom_item_res.json()["data"]["name"] == "Grandma's Homemade Mango Pickle"

        # -------------------------------------------------------------
        # Test 20 & 25: Multi-Home Isolation & Cross-Home Rejection
        # -------------------------------------------------------------
        # Home B user attempts to access Home A inventory (Blocked 403)
        cross_res = await client.get(f"/api/v1/homes/{home_a_id}/inventory/items", headers=headers_b)
        assert cross_res.status_code == 403

        # Home B attempts to assign Home A's location to its item (Blocked 400)
        cross_loc_res = await client.post(f"/api/v1/homes/{home_b_id}/inventory/items", json={
            "name": "Home B Item",
            "location_id": blue_container_id,
            "quantity": 1.0
        }, headers=headers_b)
        assert cross_loc_res.status_code == 400

        # -------------------------------------------------------------
        # Test 22, 23: Home Purchase List -> Inventory Restock Flow
        # -------------------------------------------------------------
        # Check purchase list suggestions: Basmati Rice is LOW (3kg < min 5kg, pref 10kg)
        sugg_res = await client.get(f"/api/v1/homes/{home_a_id}/purchase-list/suggestions", headers=headers_a)
        assert sugg_res.status_code == 200
        suggestions = sugg_res.json()["data"]
        assert any(s["name"] == "Basmati Rice" for s in suggestions)
        rice_sugg = next(s for s in suggestions if s["name"] == "Basmati Rice")
        assert rice_sugg["suggested_quantity"] == 7.0  # 10 - 3 = 7

        # Add item to Home Purchase List
        pur_item_res = await client.post(f"/api/v1/homes/{home_a_id}/purchase-list", json={
            "name": "Basmati Rice",
            "quantity": 7.0,
            "unit": "kg",
            "inventory_item_id": item_id,
            "notes": "Royal Basmati 7kg"
        }, headers=headers_a)
        assert pur_item_res.status_code == 201
        pur_item_id = pur_item_res.json()["data"]["id"]

        # Mark purchased with restock_inventory = True
        checkout_res = await client.post(f"/api/v1/homes/{home_a_id}/purchase-list/{pur_item_id}/purchase", json={
            "restock_inventory": True,
            "purchased_quantity": 7.0,
            "notes": "Bought at supermarket"
        }, headers=headers_a)
        assert checkout_res.status_code == 200
        assert checkout_res.json()["data"]["status"] == "PURCHASED"
        assert checkout_res.json()["data"]["restocked_to_inventory"] is True

        # Verify Inventory Item was restocked: 3kg + 7kg = 10kg, status -> GOOD
        updated_inv_res = await client.get(f"/api/v1/homes/{home_a_id}/inventory/items/{item_id}", headers=headers_a)
        assert updated_inv_res.status_code == 200
        updated_inv = updated_inv_res.json()["data"]
        assert float(updated_inv["quantity"]) == 10.0
        assert updated_inv["status"] == "GOOD"

        # Verify Purchase History record
        hist_res = await client.get(f"/api/v1/homes/{home_a_id}/purchase-history", headers=headers_a)
        assert hist_res.status_code == 200
        history_items = hist_res.json()["data"]
        assert any(h["name"] == "Basmati Rice" and float(h["quantity"]) == 7.0 for h in history_items)
