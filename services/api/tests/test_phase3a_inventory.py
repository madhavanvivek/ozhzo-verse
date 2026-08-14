import pytest
import pytest_asyncio
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from src.main import app
from src.infrastructure.database.session import Base, get_db
from src.infrastructure.database.models import (
    HomeModel,
    HomeMemberModel,
    InventoryCategoryModel,
    InventoryItemModel,
    LocationModel,
    UserModel,
    UserProfileModel
)
from src.core.security import hash_password, create_access_token


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="function")
async def db_session():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestingSessionLocal() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def setup_data(db_session: AsyncSession):
    now = datetime.now(timezone.utc)

    # 1. Verified User 1 (Admin of Home A, Member of Home B)
    user1 = UserModel(
        email="vivek@ozhzo.com",
        phone_number="+919876543210",
        password_hash=hash_password("Pass1234!"),
        is_mobile_verified=True,
        is_active=True
    )
    db_session.add(user1)
    await db_session.flush()

    prof1 = UserProfileModel(user_id=user1.id, full_name="Vivek Admin")
    db_session.add(prof1)

    # 2. Verified User 2 (Member of Home A)
    user2 = UserModel(
        email="ashraf@ozhzo.com",
        phone_number="+919876543211",
        password_hash=hash_password("Pass1234!"),
        is_mobile_verified=True,
        is_active=True
    )
    db_session.add(user2)
    await db_session.flush()

    prof2 = UserProfileModel(user_id=user2.id, full_name="Ashraf Member")
    db_session.add(prof2)

    # 3. Unverified User
    user_unverified = UserModel(
        email="unverified@ozhzo.com",
        phone_number="+919876543219",
        password_hash=hash_password("Pass1234!"),
        is_mobile_verified=False,
        is_active=True
    )
    db_session.add(user_unverified)
    await db_session.flush()

    # 4. User in Home B only
    user_home_b = UserModel(
        email="other@ozhzo.com",
        phone_number="+919876543212",
        password_hash=hash_password("Pass1234!"),
        is_mobile_verified=True,
        is_active=True
    )
    db_session.add(user_home_b)
    await db_session.flush()

    # Homes
    home_a = HomeModel(name="Madhavan Home", currency="INR", timezone="Asia/Kolkata", created_by=user1.id)
    home_b = HomeModel(name="Beach Villa", currency="USD", timezone="UTC", created_by=user_home_b.id)
    db_session.add_all([home_a, home_b])
    await db_session.flush()

    # Memberships
    # User 1 is HOME_ADMIN in Home A
    mem1_a = HomeMemberModel(home_id=home_a.id, user_id=user1.id, role="HOME_ADMIN")
    # User 2 is MEMBER in Home A
    mem2_a = HomeMemberModel(home_id=home_a.id, user_id=user2.id, role="MEMBER")
    # Unverified is Member in Home A
    mem_unv = HomeMemberModel(home_id=home_a.id, user_id=user_unverified.id, role="MEMBER")
    # User Home B is HOME_ADMIN in Home B
    mem_b = HomeMemberModel(home_id=home_b.id, user_id=user_home_b.id, role="HOME_ADMIN")

    db_session.add_all([mem1_a, mem2_a, mem_unv, mem_b])
    await db_session.commit()

    token_user1 = create_access_token({"sub": str(user1.id), "phone_number": user1.phone_number})
    token_user2 = create_access_token({"sub": str(user2.id), "phone_number": user2.phone_number})
    token_unv = create_access_token({"sub": str(user_unverified.id), "phone_number": user_unverified.phone_number})
    token_user_b = create_access_token({"sub": str(user_home_b.id), "phone_number": user_home_b.phone_number})

    return {
        "home_a": home_a,
        "home_b": home_b,
        "user1": user1,
        "user2": user2,
        "token1": token_user1,
        "token2": token_user2,
        "token_unv": token_unv,
        "token_b": token_user_b,
    }


@pytest.mark.asyncio
async def test_category_management(client: AsyncClient, setup_data: dict):
    home_id = setup_data["home_a"].id
    headers = {"Authorization": f"Bearer {setup_data['token1']}", "X-Home-Id": str(home_id)}

    # 1. Create Category
    res = await client.post(
        f"/api/v1/homes/{home_id}/inventory/categories",
        headers=headers,
        json={"name": "Pantry Essentials", "icon": "grain", "color": "#4CAF50", "sort_order": 1}
    )
    assert res.status_code == 201
    cat_id = res.json()["data"]["id"]

    # 2. Duplicate Category in same Home rejected
    res_dup = await client.post(
        f"/api/v1/homes/{home_id}/inventory/categories",
        headers=headers,
        json={"name": "Pantry Essentials"}
    )
    assert res_dup.status_code == 409

    # 3. List Categories
    res_list = await client.get(f"/api/v1/homes/{home_id}/inventory/categories", headers=headers)
    assert res_list.status_code == 200
    assert len(res_list.json()["data"]) == 1
    assert res_list.json()["data"][0]["name"] == "Pantry Essentials"


@pytest.mark.asyncio
async def test_hierarchical_locations_and_materialized_paths(client: AsyncClient, setup_data: dict):
    home_id = setup_data["home_a"].id
    headers = {"Authorization": f"Bearer {setup_data['token1']}", "X-Home-Id": str(home_id)}

    # 1. Create Root Location: Store Room
    res1 = await client.post(
        f"/api/v1/homes/{home_id}/locations",
        headers=headers,
        json={"name": "Store Room", "location_type": "ROOM", "icon": "door"}
    )
    assert res1.status_code == 201
    loc_store_id = res1.json()["data"]["id"]
    assert res1.json()["data"]["path"] == "Store Room"

    # 2. Create Child: 3rd Cupboard
    res2 = await client.post(
        f"/api/v1/homes/{home_id}/locations",
        headers=headers,
        json={"parent_id": loc_store_id, "name": "3rd Cupboard", "location_type": "FURNITURE"}
    )
    assert res2.status_code == 201
    loc_cupboard_id = res2.json()["data"]["id"]
    assert res2.json()["data"]["path"] == "Store Room > 3rd Cupboard"

    # 3. Create Grandchild: Blue Box
    res3 = await client.post(
        f"/api/v1/homes/{home_id}/locations",
        headers=headers,
        json={"parent_id": loc_cupboard_id, "name": "Blue Box", "location_type": "CONTAINER"}
    )
    assert res3.status_code == 201
    loc_box_id = res3.json()["data"]["id"]
    assert res3.json()["data"]["path"] == "Store Room > 3rd Cupboard > Blue Box"

    # 4. Duplicate sibling name rejection
    res_dup = await client.post(
        f"/api/v1/homes/{home_id}/locations",
        headers=headers,
        json={"parent_id": loc_cupboard_id, "name": "Blue Box"}
    )
    assert res_dup.status_code == 409

    # 5. List Locations as Tree
    res_tree = await client.get(f"/api/v1/homes/{home_id}/locations?as_tree=true", headers=headers)
    assert res_tree.status_code == 200
    tree = res_tree.json()["data"]
    assert len(tree) == 1
    assert tree[0]["name"] == "Store Room"
    assert len(tree[0]["children"]) == 1
    assert tree[0]["children"][0]["name"] == "3rd Cupboard"
    assert len(tree[0]["children"][0]["children"]) == 1
    assert tree[0]["children"][0]["children"][0]["name"] == "Blue Box"


@pytest.mark.asyncio
async def test_consumable_stock_and_movements(client: AsyncClient, setup_data: dict):
    home_id = setup_data["home_a"].id
    headers = {"Authorization": f"Bearer {setup_data['token1']}", "X-Home-Id": str(home_id)}

    # 1. Create Consumable Item: Basmati Rice (5.000 kg, Min 2.000 kg, Preferred 10.000 kg)
    res = await client.post(
        f"/api/v1/homes/{home_id}/inventory/items",
        headers=headers,
        json={
            "item_type": "CONSUMABLE",
            "name": "Basmati Rice",
            "quantity": 5.000,
            "unit": "kg",
            "min_threshold": 2.000,
            "preferred_quantity": 10.000
        }
    )
    assert res.status_code == 201
    item = res.json()["data"]
    item_id = item["id"]
    assert item["status"] == "GOOD"
    assert Decimal(str(item["quantity"])) == Decimal("5.000")

    # 2. Consume 3.500 kg (Remaining: 1.500 kg -> LOW stock threshold reached)
    res_consume = await client.post(
        f"/api/v1/homes/{home_id}/inventory/items/{item_id}/movements",
        headers=headers,
        json={"movement_type": "CONSUME", "quantity": 3.500, "reason": "Family Dinner"}
    )
    assert res_consume.status_code == 200
    move = res_consume.json()["data"]
    assert Decimal(str(move["quantity_delta"])) == Decimal("-3.500")
    assert Decimal(str(move["resulting_quantity"])) == Decimal("1.500")

    # Verify Item Status is now LOW
    res_item = await client.get(f"/api/v1/homes/{home_id}/inventory/items/{item_id}", headers=headers)
    assert res_item.json()["data"]["status"] == "LOW"

    # 3. Consume remaining 1.500 kg -> OUT_OF_STOCK
    await client.post(
        f"/api/v1/homes/{home_id}/inventory/items/{item_id}/movements",
        headers=headers,
        json={"movement_type": "CONSUME", "quantity": 1.500, "reason": "Lunch"}
    )
    res_out = await client.get(f"/api/v1/homes/{home_id}/inventory/items/{item_id}", headers=headers)
    assert res_out.json()["data"]["status"] == "OUT_OF_STOCK"

    # 4. Restock: ADD 10.000 kg -> GOOD
    await client.post(
        f"/api/v1/homes/{home_id}/inventory/items/{item_id}/movements",
        headers=headers,
        json={"movement_type": "ADD", "quantity": 10.000, "reason": "Monthly Grocery Restock"}
    )
    res_good = await client.get(f"/api/v1/homes/{home_id}/inventory/items/{item_id}", headers=headers)
    assert res_good.json()["data"]["status"] == "GOOD"
    assert Decimal(str(res_good.json()["data"]["quantity"])) == Decimal("10.000")

    # 5. Verify Movements Ledger History
    res_ledger = await client.get(f"/api/v1/homes/{home_id}/inventory/items/{item_id}/movements", headers=headers)
    assert res_ledger.status_code == 200
    movements = res_ledger.json()["data"]
    # Initial + Consume 3.5 + Consume 1.5 + Add 10 = 4 records
    assert len(movements) == 4


@pytest.mark.asyncio
async def test_asset_location_movements_and_last_seen(client: AsyncClient, setup_data: dict):
    home_id = setup_data["home_a"].id
    headers = {"Authorization": f"Bearer {setup_data['token1']}", "X-Home-Id": str(home_id)}

    # Create 2 Locations
    loc1 = (await client.post(f"/api/v1/homes/{home_id}/locations", headers=headers, json={"name": "Store Room"})).json()["data"]
    loc2 = (await client.post(f"/api/v1/homes/{home_id}/locations", headers=headers, json={"name": "Garage"})).json()["data"]

    # 1. Create Asset: Cordless Drill placed in Store Room
    res = await client.post(
        f"/api/v1/homes/{home_id}/inventory/items",
        headers=headers,
        json={
            "item_type": "ASSET",
            "name": "Cordless Drill",
            "location_id": loc1["id"],
            "condition": "EXCELLENT"
        }
    )
    assert res.status_code == 201
    asset = res.json()["data"]
    asset_id = asset["id"]
    assert asset["location_path"] == "Store Room"
    assert asset["asset_status"] == "AVAILABLE"

    # 2. Relocate Asset to Garage
    res_move = await client.post(
        f"/api/v1/homes/{home_id}/inventory/items/{asset_id}/move",
        headers=headers,
        json={"to_location_id": loc2["id"], "reason": "Moving tools to garage workbench"}
    )
    assert res_move.status_code == 200
    moved_asset = res_move.json()["data"]
    assert moved_asset["location_path"] == "Garage"
    assert moved_asset["last_seen_location_id"] == loc2["id"]

    # 3. Check Location Movement History
    res_hist = await client.get(f"/api/v1/homes/{home_id}/inventory/items/{asset_id}/location-history", headers=headers)
    assert res_hist.status_code == 200
    history = res_hist.json()["data"]
    assert len(history) >= 1
    assert history[0]["to_location_path"] == "Garage"
    assert history[0]["from_location_path"] == "Store Room"


@pytest.mark.asyncio
async def test_asset_lending_borrowing_and_return(client: AsyncClient, setup_data: dict):
    home_id = setup_data["home_a"].id
    headers = {"Authorization": f"Bearer {setup_data['token1']}", "X-Home-Id": str(home_id)}

    # Create Asset: Toolkit
    res_asset = await client.post(
        f"/api/v1/homes/{home_id}/inventory/items",
        headers=headers,
        json={"item_type": "ASSET", "name": "Heavy Duty Toolkit"}
    )
    asset_id = res_asset.json()["data"]["id"]

    # 1. Borrow Asset (Lend to Ashraf)
    res_borrow = await client.post(
        f"/api/v1/homes/{home_id}/inventory/items/{asset_id}/borrow",
        headers=headers,
        json={
            "borrower_name": "Ashraf",
            "borrower_type": "MEMBER",
            "borrower_contact": "+919876543211",
            "notes": "Home shelving installation"
        }
    )
    assert res_borrow.status_code == 200
    loan = res_borrow.json()["data"]
    assert loan["loan_status"] == "ACTIVE"
    assert loan["borrower_name"] == "Ashraf"

    # Verify Asset is marked BORROWED
    res_item = await client.get(f"/api/v1/homes/{home_id}/inventory/items/{asset_id}", headers=headers)
    assert res_item.json()["data"]["asset_status"] == "BORROWED"
    assert res_item.json()["data"]["current_holder_name"] == "Ashraf"

    # 2. Prevent Double Borrowing
    res_double = await client.post(
        f"/api/v1/homes/{home_id}/inventory/items/{asset_id}/borrow",
        headers=headers,
        json={"borrower_name": "Karthika"}
    )
    assert res_double.status_code == 400

    # 3. Return Asset
    res_return = await client.post(
        f"/api/v1/homes/{home_id}/inventory/items/{asset_id}/return",
        headers=headers,
        json={"notes": "Returned in perfect condition"}
    )
    assert res_return.status_code == 200
    returned_loan = res_return.json()["data"]
    assert returned_loan["loan_status"] == "RETURNED"

    # Verify Asset is marked AVAILABLE again
    res_avail = await client.get(f"/api/v1/homes/{home_id}/inventory/items/{asset_id}", headers=headers)
    assert res_avail.json()["data"]["asset_status"] == "AVAILABLE"
    assert res_avail.json()["data"]["current_holder_name"] is None

    # 4. Prevent Double Return
    res_double_ret = await client.post(
        f"/api/v1/homes/{home_id}/inventory/items/{asset_id}/return",
        headers=headers,
        json={}
    )
    assert res_double_ret.status_code == 400

    # 5. Loan History
    res_loans = await client.get(f"/api/v1/homes/{home_id}/inventory/items/{asset_id}/loans", headers=headers)
    assert res_loans.status_code == 200
    assert len(res_loans.json()["data"]) == 1


@pytest.mark.asyncio
async def test_cross_home_security_isolation(client: AsyncClient, setup_data: dict):
    home_a_id = setup_data["home_a"].id
    home_b_id = setup_data["home_b"].id
    headers_a = {"Authorization": f"Bearer {setup_data['token1']}", "X-Home-Id": str(home_a_id)}
    headers_b = {"Authorization": f"Bearer {setup_data['token_b']}", "X-Home-Id": str(home_b_id)}

    # Create item in Home A
    res_a = await client.post(
        f"/api/v1/homes/{home_a_id}/inventory/items",
        headers=headers_a,
        json={"name": "Home A Secret Item"}
    )
    item_a_id = res_a.json()["data"]["id"]

    # User B (in Home B) attempts to read Home A item via Home A endpoint -> 403 Forbidden
    res_forbidden1 = await client.get(
        f"/api/v1/homes/{home_a_id}/inventory/items/{item_a_id}",
        headers={"Authorization": f"Bearer {setup_data['token_b']}", "X-Home-Id": str(home_a_id)}
    )
    assert res_forbidden1.status_code == 403

    # User B attempts to access item_a_id via Home B path -> 404 Not Found (isolated)
    res_forbidden2 = await client.get(
        f"/api/v1/homes/{home_b_id}/inventory/items/{item_a_id}",
        headers=headers_b
    )
    assert res_forbidden2.status_code == 404

    # Unverified mobile user attempts access -> 403 Forbidden
    res_unv = await client.get(
        f"/api/v1/homes/{home_a_id}/inventory/items",
        headers={"Authorization": f"Bearer {setup_data['token_unv']}", "X-Home-Id": str(home_a_id)}
    )
    assert res_unv.status_code == 403


@pytest.mark.asyncio
async def test_universal_search_and_summary(client: AsyncClient, setup_data: dict):
    home_id = setup_data["home_a"].id
    headers = {"Authorization": f"Bearer {setup_data['token1']}", "X-Home-Id": str(home_id)}

    # Create Location: Tool Rack
    loc = (await client.post(f"/api/v1/homes/{home_id}/locations", headers=headers, json={"name": "Tool Rack"})).json()["data"]

    # Create 3 items
    await client.post(
        f"/api/v1/homes/{home_id}/inventory/items",
        headers=headers,
        json={"name": "Electric Screwdriver", "item_type": "ASSET", "location_id": loc["id"]}
    )
    await client.post(
        f"/api/v1/homes/{home_id}/inventory/items",
        headers=headers,
        json={"name": "Almond Milk", "item_type": "CONSUMABLE", "quantity": 1.0, "min_threshold": 2.0}
    )
    await client.post(
        f"/api/v1/homes/{home_id}/inventory/items",
        headers=headers,
        json={"name": "Whole Wheat Flour", "item_type": "CONSUMABLE", "quantity": 10.0, "min_threshold": 2.0}
    )

    # 1. Search by item name prefix
    res_search1 = await client.get(f"/api/v1/homes/{home_id}/inventory/items?search=Screwdriver", headers=headers)
    assert res_search1.status_code == 200
    assert len(res_search1.json()["data"]["items"]) == 1
    assert res_search1.json()["data"]["items"][0]["name"] == "Electric Screwdriver"

    # 2. Search by location name (finds items in Tool Rack)
    res_search2 = await client.get(f"/api/v1/homes/{home_id}/inventory/items?search=Tool Rack", headers=headers)
    assert res_search2.status_code == 200
    assert len(res_search2.json()["data"]["items"]) == 1

    # 3. Verify Summary KPIs
    res_sum = await client.get(f"/api/v1/homes/{home_id}/inventory/summary", headers=headers)
    assert res_sum.status_code == 200
    sum_data = res_sum.json()["data"]
    assert sum_data["total_items"] == 3
    assert sum_data["assets_count"] == 1
    assert sum_data["consumables_count"] == 2
    assert sum_data["low_stock_count"] == 1  # Almond Milk (1 <= 2)
    assert sum_data["good_stock_count"] == 2  # Screwdriver + Wheat Flour
