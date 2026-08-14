#!/usr/bin/env python3
"""
Ozhzo Verse — Development Household Seed Script
=============================================================================
WARNING: DEVELOPMENT & TESTING ONLY!
DO NOT EXECUTE IN PRODUCTION!
=============================================================================
Populates a realistic demo household with hierarchical locations, consumable
supplies, durable assets, tasks, bills, calendar events, and purchase items.
"""

import asyncio
import os
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

# Add services/api to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../services/api")))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.core.config import settings
from src.core.security import get_password_hash
from src.infrastructure.database.models import (
    BillCategoryModel,
    BillModel,
    EventCategoryModel,
    EventModel,
    EventParticipantModel,
    HomeMemberModel,
    HomeModel,
    InventoryCategoryModel,
    InventoryItemModel,
    LocationModel,
    PurchaseItemModel,
    PurchaseListModel,
    TaskCategoryModel,
    TaskModel,
    UserModel,
    UserProfileModel
)


async def seed_demo_household():
    if settings.ENVIRONMENT == "production":
        print("ERROR: Refusing to seed demo data into PRODUCTION environment!")
        sys.exit(1)

    print("==> Starting Ozhzo Verse Development Household Seeding...")
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # 1. Create Demo Users
        user_owner_id = uuid4()
        user_member_id = uuid4()

        owner = UserModel(
            id=user_owner_id,
            email="demo_owner@ozhzo.com",
            password_hash=get_password_hash("DemoPassword123!"),
            is_active=True,
            is_verified=True,
            mobile_verified=True
        )
        owner_profile = UserProfileModel(
            id=uuid4(),
            user_id=user_owner_id,
            display_name="Alex Rivera",
            phone_number="+15550100",
            timezone="America/New_York"
        )

        member = UserModel(
            id=user_member_id,
            email="demo_member@ozhzo.com",
            password_hash=get_password_hash("DemoPassword123!"),
            is_active=True,
            is_verified=True,
            mobile_verified=True
        )
        member_profile = UserProfileModel(
            id=uuid4(),
            user_id=user_member_id,
            display_name="Sarah Rivera",
            phone_number="+15550101",
            timezone="America/New_York"
        )

        session.add_all([owner, owner_profile, member, member_profile])
        await session.flush()

        # 2. Create Demo Home
        home_id = uuid4()
        home = HomeModel(
            id=home_id,
            name="Demo Family Home",
            currency="USD",
            timezone="America/New_York",
            created_by=user_owner_id,
            status="ACTIVE"
        )
        session.add(home)

        # Add Memberships
        m1 = HomeMemberModel(id=uuid4(), home_id=home_id, user_id=user_owner_id, role="HOME_ADMIN", status="ACTIVE")
        m2 = HomeMemberModel(id=uuid4(), home_id=home_id, user_id=user_member_id, role="MEMBER", status="ACTIVE")
        session.add_all([m1, m2])
        await session.flush()

        # 3. Create Hierarchical Locations
        loc_kitchen = LocationModel(id=uuid4(), home_id=home_id, name="Kitchen", location_type="ROOM", path="Kitchen")
        session.add(loc_kitchen)
        await session.flush()

        loc_pantry = LocationModel(id=uuid4(), home_id=home_id, name="Pantry", location_type="FURNITURE", parent_id=loc_kitchen.id, path="Kitchen ➔ Pantry")
        session.add(loc_pantry)
        await session.flush()

        loc_shelf2 = LocationModel(id=uuid4(), home_id=home_id, name="2nd Shelf", location_type="SHELF", parent_id=loc_pantry.id, path="Kitchen ➔ Pantry ➔ 2nd Shelf")
        session.add(loc_shelf2)
        await session.flush()

        loc_blue_box = LocationModel(id=uuid4(), home_id=home_id, name="Blue Box", location_type="CONTAINER", parent_id=loc_shelf2.id, path="Kitchen ➔ Pantry ➔ 2nd Shelf ➔ Blue Box")
        session.add(loc_blue_box)

        loc_store_room = LocationModel(id=uuid4(), home_id=home_id, name="Store Room", location_type="ROOM", path="Store Room")
        session.add(loc_store_room)
        await session.flush()

        loc_cupboard = LocationModel(id=uuid4(), home_id=home_id, name="3rd Cupboard", location_type="FURNITURE", parent_id=loc_store_room.id, path="Store Room ➔ 3rd Cupboard")
        session.add(loc_cupboard)
        await session.flush()

        loc_tool_box = LocationModel(id=uuid4(), home_id=home_id, name="Tool Box", location_type="CONTAINER", parent_id=loc_cupboard.id, path="Store Room ➔ 3rd Cupboard ➔ Tool Box")
        session.add(loc_tool_box)

        loc_garage = LocationModel(id=uuid4(), home_id=home_id, name="Garage", location_type="ROOM", path="Garage")
        session.add(loc_garage)
        await session.flush()

        loc_workshop = LocationModel(id=uuid4(), home_id=home_id, name="Workshop", location_type="AREA", parent_id=loc_garage.id, path="Garage ➔ Workshop")
        session.add(loc_workshop)
        await session.flush()

        # 4. Create Durable Assets
        assets = [
            InventoryItemModel(
                id=uuid4(), home_id=home_id, name="Mechanic Precision Toolkit", item_type="ASSET",
                location_id=loc_tool_box.id, location_path="Store Room ➔ 3rd Cupboard ➔ Tool Box",
                asset_status="AVAILABLE", condition="EXCELLENT", created_by=user_owner_id
            ),
            InventoryItemModel(
                id=uuid4(), home_id=home_id, name="Front Door Spare Keys", item_type="ASSET",
                location_id=loc_blue_box.id, location_path="Kitchen ➔ Pantry ➔ 2nd Shelf ➔ Blue Box",
                asset_status="AVAILABLE", condition="GOOD", created_by=user_owner_id
            ),
            InventoryItemModel(
                id=uuid4(), home_id=home_id, name="Aluminum Step Ladder 6ft", item_type="ASSET",
                location_id=loc_garage.id, location_path="Garage",
                asset_status="AVAILABLE", condition="GOOD", created_by=user_owner_id
            ),
            InventoryItemModel(
                id=uuid4(), home_id=home_id, name="Heavy Duty Extension Cable 25m", item_type="ASSET",
                location_id=loc_workshop.id, location_path="Garage ➔ Workshop",
                asset_status="AVAILABLE", condition="GOOD", created_by=user_owner_id
            )
        ]
        session.add_all(assets)

        # 5. Create Consumable Inventory Supplies
        supplies = [
            InventoryItemModel(
                id=uuid4(), home_id=home_id, name="Basmati Rice Royal", item_type="CONSUMABLE",
                quantity=Decimal("4.5"), unit="kg", min_threshold=Decimal("3.0"),
                location_id=loc_shelf2.id, location_path="Kitchen ➔ Pantry ➔ 2nd Shelf",
                status="IN_STOCK", created_by=user_owner_id
            ),
            InventoryItemModel(
                id=uuid4(), home_id=home_id, name="Organic Whole Milk", item_type="CONSUMABLE",
                quantity=Decimal("1.0"), unit="L", min_threshold=Decimal("2.0"),
                location_id=loc_kitchen.id, location_path="Kitchen",
                status="LOW_STOCK", created_by=user_owner_id
            ),
            InventoryItemModel(
                id=uuid4(), home_id=home_id, name="Extra Virgin Olive Oil", item_type="CONSUMABLE",
                quantity=Decimal("2.0"), unit="L", min_threshold=Decimal("1.0"),
                location_id=loc_pantry.id, location_path="Kitchen ➔ Pantry",
                status="IN_STOCK", created_by=user_owner_id
            ),
            InventoryItemModel(
                id=uuid4(), home_id=home_id, name="Cane Sugar", item_type="CONSUMABLE",
                quantity=Decimal("1.5"), unit="kg", min_threshold=Decimal("1.0"),
                location_id=loc_pantry.id, location_path="Kitchen ➔ Pantry",
                status="IN_STOCK", created_by=user_owner_id
            ),
            InventoryItemModel(
                id=uuid4(), home_id=home_id, name="All-Purpose Cleaning Spray", item_type="CONSUMABLE",
                quantity=Decimal("0.0"), unit="bottles", min_threshold=Decimal("1.0"),
                location_id=loc_kitchen.id, location_path="Kitchen",
                status="OUT_OF_STOCK", created_by=user_owner_id
            )
        ]
        session.add_all(supplies)

        # 6. Create Purchase List & Items
        p_list = PurchaseListModel(id=uuid4(), home_id=home_id, name="Weekly Groceries", created_by=user_owner_id)
        session.add(p_list)
        await session.flush()

        p_items = [
            PurchaseItemModel(id=uuid4(), home_id=home_id, purchase_list_id=p_list.id, name="Basmati Rice (5 kg)", quantity=Decimal("5.0"), unit="kg", priority="HIGH", is_checked=False),
            PurchaseItemModel(id=uuid4(), home_id=home_id, purchase_list_id=p_list.id, name="Organic Whole Milk (2 L)", quantity=Decimal("2.0"), unit="L", priority="HIGH", is_checked=False),
            PurchaseItemModel(id=uuid4(), home_id=home_id, purchase_list_id=p_list.id, name="Cleaning Liquid Refill", quantity=Decimal("1.0"), unit="bottles", priority="NORMAL", is_checked=False)
        ]
        session.add_all(p_items)

        # 7. Create Tasks & Chores
        today = date.today()
        tasks = [
            TaskModel(id=uuid4(), home_id=home_id, title="Clean Water Filter Cartridge", due_date=today, priority="HIGH", status="TODO", assigned_to=user_owner_id, created_by=user_owner_id),
            TaskModel(id=uuid4(), home_id=home_id, title="Service Living Room AC", due_date=today + timedelta(days=5), priority="NORMAL", status="TODO", assigned_to=user_member_id, created_by=user_owner_id),
            TaskModel(id=uuid4(), home_id=home_id, title="Organize Garage Workshop Tools", due_date=today + timedelta(days=2), priority="LOW", status="TODO", assigned_to=user_owner_id, created_by=user_owner_id)
        ]
        session.add_all(tasks)

        # 8. Create Bills & Financial Records
        bills = [
            BillModel(id=uuid4(), home_id=home_id, title="City Electricity Utility", expected_amount=Decimal("145.50"), amount_paid=Decimal("0.00"), currency="USD", due_date=today, status="UNPAID", created_by=user_owner_id),
            BillModel(id=uuid4(), home_id=home_id, title="Fiber High Speed Internet", expected_amount=Decimal("79.99"), amount_paid=Decimal("0.00"), currency="USD", due_date=today + timedelta(days=10), status="UNPAID", created_by=user_owner_id),
            BillModel(id=uuid4(), home_id=home_id, title="Municipal Water & Sewage", expected_amount=Decimal("45.00"), amount_paid=Decimal("0.00"), currency="USD", due_date=today + timedelta(days=15), status="UNPAID", created_by=user_owner_id)
        ]
        session.add_all(bills)

        # 9. Create Calendar Events
        now_utc = datetime.now(timezone.utc)
        event1 = EventModel(
            id=uuid4(), home_id=home_id, title="Grandmother's 80th Birthday Celebration",
            start_time=now_utc + timedelta(hours=2), end_time=now_utc + timedelta(hours=6),
            is_all_day=False, location="Family Home Dining Room", status="CONFIRMED", created_by=user_owner_id
        )
        event2 = EventModel(
            id=uuid4(), home_id=home_id, title="Pediatrician Doctor Appointment",
            start_time=now_utc + timedelta(days=3, hours=10), end_time=now_utc + timedelta(days=3, hours=11),
            is_all_day=False, location="City Health Clinic", status="CONFIRMED", created_by=user_owner_id
        )
        session.add_all([event1, event2])
        await session.flush()

        part1 = EventParticipantModel(id=uuid4(), event_id=event1.id, user_id=user_member_id, status="ACCEPTED")
        session.add(part1)

        await session.commit()
        print("==> Demo Family Home successfully seeded! (100%)")
        print(f" -> Home ID: {home_id}")
        print(f" -> Owner Login: demo_owner@ozhzo.com / DemoPassword123!")
        print(f" -> Member Login: demo_member@ozhzo.com / DemoPassword123!")


if __name__ == "__main__":
    asyncio.run(seed_demo_household())
