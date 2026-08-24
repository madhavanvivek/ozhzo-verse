import pytest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import HTTPException
from src.api.dependencies import HomeContext
from src.api.v1.inventory import (
    calculate_warranty_status,
    create_inventory_item,
    get_inventory_item,
    get_item_qr_label,
    list_inventory_items,
    update_inventory_item,
)
from src.infrastructure.database.models import (
    InventoryCategoryModel,
    InventoryItemModel,
    LocationModel,
    UserModel,
)
from src.schemas.inventory import (
    CreateInventoryItemRequest,
    UpdateInventoryItemRequest,
)


@pytest.fixture
def mock_home_context():
    user = MagicMock(spec=UserModel)
    user.id = uuid4()
    user.email = "owner@ozhzo.com"
    user.is_super_admin = False
    user.system_role = "USER"

    ctx = MagicMock(spec=HomeContext)
    ctx.home_id = uuid4()
    ctx.user = user
    ctx.role = "OWNER"
    ctx.permissions = ["inventory:view", "inventory:create", "inventory:edit", "inventory:delete"]
    return ctx


@pytest.mark.asyncio
async def test_01_create_asset_with_warranty_and_identification(mock_home_context):
    db = AsyncMock()
    
    # Mock location lookup
    loc_id = uuid4()
    loc_mock = MagicMock(spec=LocationModel)
    loc_mock.id = loc_id
    loc_mock.name = "Garage Workshop"
    
    scalar_mock = MagicMock()
    scalar_mock.scalar_one_or_none.return_value = loc_mock
    db.execute.return_value = scalar_mock

    # Mock get category
    db.get.return_value = None

    warranty_date = date.today() + timedelta(days=365)
    purchase_date = date.today() - timedelta(days=30)

    payload = CreateInventoryItemRequest(
        name="Bosch Professional Hammer Drill",
        item_type="ASSET",
        location_id=loc_id,
        quantity=Decimal("1.000"),
        unit="pcs",
        condition="EXCELLENT",
        brand="Bosch",
        model_number="GBH 2-26 DRE",
        serial_number="SN-BOSCH-987654",
        barcode="3165140344333",
        purchase_date=purchase_date,
        purchase_price=Decimal("12500.00"),
        purchase_store="Amazon India",
        warranty_expiry_date=warranty_date,
        warranty_notes="3-year extended domestic warranty",
        photo_url="https://images.ozhzo.com/tools/bosch_drill.jpg",
        receipt_url="https://docs.ozhzo.com/receipts/bosch_drill_inv.pdf",
        manual_url="https://docs.ozhzo.com/manuals/bosch_gbh2-26.pdf",
        last_serviced_at=date.today(),
        next_service_due_at=date.today() + timedelta(days=180),
        service_notes="Initial inspection and greasing completed."
    )

    with patch("src.api.v1.inventory.build_location_path_map", return_value={loc_id: "Garage ➔ Workshop"}):
        res = await create_inventory_item(payload=payload, home_ctx=mock_home_context, db=db)

    assert res.success is True
    data = res.data
    assert data.name == "Bosch Professional Hammer Drill"
    assert data.item_type == "ASSET"
    assert data.brand == "Bosch"
    assert data.model_number == "GBH 2-26 DRE"
    assert data.serial_number == "SN-BOSCH-987654"
    assert data.barcode == "3165140344333"
    assert data.purchase_price == Decimal("12500.00")
    assert data.purchase_store == "Amazon India"
    assert data.warranty_expiry_date == warranty_date
    assert data.warranty_status == "ACTIVE"
    assert data.warranty_notes == "3-year extended domestic warranty"
    assert data.receipt_url == "https://docs.ozhzo.com/receipts/bosch_drill_inv.pdf"
    assert data.manual_url == "https://docs.ozhzo.com/manuals/bosch_gbh2-26.pdf"
    assert data.photo_url == "https://images.ozhzo.com/tools/bosch_drill.jpg"


def test_02_calculate_warranty_status_lifecycle():
    today = date.today()
    
    # 1. No warranty
    assert calculate_warranty_status(None) == "NO_WARRANTY"

    # 2. Expired (in past)
    expired_date = today - timedelta(days=5)
    assert calculate_warranty_status(expired_date) == "EXPIRED"

    # 3. Expiring soon (within 30 days)
    expiring_soon_date = today + timedelta(days=15)
    assert calculate_warranty_status(expiring_soon_date) == "EXPIRING_SOON"

    # 4. Active (more than 30 days away)
    active_date = today + timedelta(days=90)
    assert calculate_warranty_status(active_date) == "ACTIVE"


@pytest.mark.asyncio
async def test_03_update_asset_maintenance_and_documents(mock_home_context):
    db = AsyncMock()
    item_id = uuid4()
    
    existing_item = InventoryItemModel(
        id=item_id,
        home_id=mock_home_context.home_id,
        name="Dyson V12 Cordless Vacuum",
        item_type="ASSET",
        quantity=Decimal("1.000"),
        unit="pcs",
        brand="Dyson",
        model_number="V12 Slim",
        serial_number="DYSON-V12-001",
        deleted_at=None
    )

    scalar_mock = MagicMock()
    scalar_mock.scalar_one_or_none.return_value = existing_item
    db.execute.return_value = scalar_mock
    db.get.return_value = None

    service_date = date.today()
    next_due = date.today() + timedelta(days=90)
    warranty_date = date.today() + timedelta(days=20) # Expiring soon

    payload = UpdateInventoryItemRequest(
        warranty_expiry_date=warranty_date,
        warranty_notes="Filter replacement eligible",
        last_serviced_at=service_date,
        next_service_due_at=next_due,
        service_notes="HEPA filter washed and motor battery tested at 98%",
        receipt_url="https://docs.ozhzo.com/dyson_receipt.pdf"
    )

    with patch("src.api.v1.inventory.build_location_path_map", return_value={}):
        res = await update_inventory_item(item_id=item_id, payload=payload, home_ctx=mock_home_context, db=db)

    assert res.success is True
    data = res.data
    assert data.warranty_expiry_date == warranty_date
    assert data.warranty_status == "EXPIRING_SOON"
    assert data.last_serviced_at == service_date
    assert data.next_service_due_at == next_due
    assert data.service_notes == "HEPA filter washed and motor battery tested at 98%"
    assert data.receipt_url == "https://docs.ozhzo.com/dyson_receipt.pdf"


@pytest.mark.asyncio
async def test_04_get_item_qr_label_endpoint(mock_home_context):
    db = AsyncMock()
    item_id = uuid4()
    loc_id = uuid4()

    item = InventoryItemModel(
        id=item_id,
        home_id=mock_home_context.home_id,
        name="Makita Angle Grinder",
        item_type="ASSET",
        location_id=loc_id,
        serial_number="MAKITA-9557NB",
        barcode="088381096751",
        deleted_at=None
    )

    scalar_mock = MagicMock()
    scalar_mock.scalar_one_or_none.return_value = item
    db.execute.return_value = scalar_mock

    with patch("src.api.v1.inventory.build_location_path_map", return_value={loc_id: "Garage ➔ Tool Cabinet ➔ Shelf 1"}):
        res = await get_item_qr_label(item_id=item_id, home_ctx=mock_home_context, db=db)

    assert res.success is True
    label = res.data
    assert label.item_id == item_id
    assert label.item_name == "Makita Angle Grinder"
    assert label.item_type == "ASSET"
    assert label.location_path == "Garage ➔ Tool Cabinet ➔ Shelf 1"
    assert label.serial_number == "MAKITA-9557NB"
    assert label.barcode == "088381096751"
    assert f"OZHZO:ASSET:{mock_home_context.home_id}:{item_id}" in label.qr_payload


@pytest.mark.asyncio
async def test_05_create_custom_location_and_sub_location(mock_home_context):
    from src.api.v1.locations import create_location
    from src.schemas.inventory import CreateLocationRequest

    db = AsyncMock()
    parent_loc_id = uuid4()
    parent_loc = LocationModel(
        id=parent_loc_id,
        home_id=mock_home_context.home_id,
        name="Garage",
        location_type="ROOM"
    )

    # 1. Mock parent lookup and duplicate check
    mock_res_parent = MagicMock()
    mock_res_parent.scalar_one_or_none.return_value = parent_loc

    mock_res_dup = MagicMock()
    mock_res_dup.scalar_one_or_none.return_value = None

    db.execute.side_effect = [mock_res_parent, mock_res_dup]

    payload = CreateLocationRequest(
        parent_id=parent_loc_id,
        name="Heavy Tool Rack",
        location_type="Garage Cabinet",
        description="Heavy metal storage rack in corner"
    )

    with patch("src.api.v1.locations.build_location_path_map", return_value={parent_loc_id: "Garage"}):
        res = await create_location(payload=payload, home_ctx=mock_home_context, db=db)

    assert res.success is True
    assert res.data.name == "Heavy Tool Rack"
    assert res.data.location_type == "Garage Cabinet"
    assert res.data.parent_id == parent_loc_id


@pytest.mark.asyncio
async def test_06_update_location_and_prevent_self_parent(mock_home_context):
    from src.api.v1.locations import update_location
    from src.schemas.inventory import UpdateLocationRequest

    db = AsyncMock()
    loc_id = uuid4()
    loc = LocationModel(
        id=loc_id,
        home_id=mock_home_context.home_id,
        name="Shelf A",
        location_type="SHELF"
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = loc
    db.execute.return_value = mock_res

    # 1. Update location details
    payload = UpdateLocationRequest(
        name="Shelf A (Top)",
        location_type="SHELF",
        description="Top shelf for electronics"
    )

    with patch("src.api.v1.locations.build_location_path_map", return_value={loc_id: "Shelf A (Top)"}):
        res = await update_location(location_id=loc_id, payload=payload, home_ctx=mock_home_context, db=db)

    assert res.success is True
    assert loc.name == "Shelf A (Top)"
    assert loc.description == "Top shelf for electronics"

    # 2. Self parent check
    with pytest.raises(HTTPException) as exc:
        await update_location(location_id=loc_id, payload=UpdateLocationRequest(parent_id=loc_id), home_ctx=mock_home_context, db=db)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_07_delete_location_and_cross_home_isolation(mock_home_context):
    from src.api.v1.locations import delete_location

    db = AsyncMock()
    loc_id = uuid4()
    loc = LocationModel(
        id=loc_id,
        home_id=mock_home_context.home_id,
        name="Old Storage Box",
        location_type="CONTAINER"
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = loc
    db.execute.return_value = mock_res

    res = await delete_location(location_id=loc_id, home_ctx=mock_home_context, db=db)
    assert res.success is True
    assert loc.deleted_at is not None

    # Cross home check
    mock_res_none = MagicMock()
    mock_res_none.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_res_none

    with pytest.raises(HTTPException) as exc:
        await delete_location(location_id=uuid4(), home_ctx=mock_home_context, db=db)
    assert exc.value.status_code == 404
