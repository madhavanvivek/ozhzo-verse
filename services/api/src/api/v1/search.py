from typing import Dict, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, require_home_permission, HomeContext
from src.infrastructure.database.session import get_db
from src.infrastructure.database.models import (
    AssetLoanModel,
    BillModel,
    EventModel,
    HomeMemberModel,
    InventoryItemModel,
    LocationModel,
    PurchaseItemModel,
    TaskModel,
    UserModel
)
from src.schemas.common import ApiSuccessResponse
from src.schemas.search import SearchResultItemDTO, UnifiedSearchResponse

router = APIRouter(prefix="/homes/{home_id}/search", tags=["Unified Search"])


@router.get("", response_model=ApiSuccessResponse[UnifiedSearchResponse])
async def unified_home_search(
    q: str = Query(..., min_length=1, max_length=100, description="Search query string"),
    domain: Optional[str] = Query(None, description="Optional domain filter (INVENTORY, ASSET, LOCATION, PURCHASE, TASK, BILL, EVENT, MEMBER)"),
    limit_per_domain: int = Query(5, ge=1, le=20),
    home_ctx: HomeContext = Depends(require_home_permission("home:view")),
    db: AsyncSession = Depends(get_db),
):
    query_clean = q.strip()
    term = f"%{query_clean}%"

    results: List[SearchResultItemDTO] = []
    domain_counts: Dict[str, int] = {
        "ASSET": 0,
        "INVENTORY": 0,
        "LOCATION": 0,
        "PURCHASE": 0,
        "TASK": 0,
        "BILL": 0,
        "EVENT": 0,
        "MEMBER": 0,
    }

    # 1. Search Durable Assets
    if not domain or domain == "ASSET":
        asset_q = (
            select(InventoryItemModel)
            .where(
                InventoryItemModel.home_id == home_ctx.home_id,
                InventoryItemModel.deleted_at.is_(None),
                InventoryItemModel.item_type == "ASSET",
                or_(
                    InventoryItemModel.name.ilike(term),
                    InventoryItemModel.location_path.ilike(term),
                    InventoryItemModel.description.ilike(term),
                    InventoryItemModel.notes.ilike(term),
                    InventoryItemModel.current_holder_name.ilike(term)
                )
            )
            .limit(limit_per_domain)
        )
        asset_items = (await db.execute(asset_q)).scalars().all()
        for a in asset_items:
            loc_str = f"Location: {a.location_path}" if a.location_path else "Unassigned"
            holder_str = f" • With: {a.current_holder_name}" if a.current_holder_name else ""
            results.append(
                SearchResultItemDTO(
                    id=a.id,
                    domain="ASSET",
                    title=a.name,
                    subtitle=f"{loc_str}{holder_str}",
                    location_path=a.location_path,
                    status=a.asset_status,
                    relevance=1.0,
                    navigation_target=f"/inventory/assets/{a.id}",
                    meta_info={"condition": a.condition, "holder": a.current_holder_name}
                )
            )
        domain_counts["ASSET"] = len(asset_items)

    # 2. Search Consumable Inventory Supplies
    if not domain or domain == "INVENTORY":
        inv_q = (
            select(InventoryItemModel)
            .where(
                InventoryItemModel.home_id == home_ctx.home_id,
                InventoryItemModel.deleted_at.is_(None),
                InventoryItemModel.item_type == "CONSUMABLE",
                or_(
                    InventoryItemModel.name.ilike(term),
                    InventoryItemModel.location_path.ilike(term),
                    InventoryItemModel.notes.ilike(term)
                )
            )
            .limit(limit_per_domain)
        )
        inv_items = (await db.execute(inv_q)).scalars().all()
        for item in inv_items:
            loc_str = f" • Location: {item.location_path}" if item.location_path else ""
            results.append(
                SearchResultItemDTO(
                    id=item.id,
                    domain="INVENTORY",
                    title=item.name,
                    subtitle=f"{item.quantity} {item.unit}{loc_str}",
                    location_path=item.location_path,
                    status=item.status,
                    relevance=0.9,
                    navigation_target=f"/inventory/{item.id}",
                    meta_info={"quantity": str(item.quantity), "unit": item.unit}
                )
            )
        domain_counts["INVENTORY"] = len(inv_items)

    # 3. Search Physical Locations
    if not domain or domain == "LOCATION":
        loc_q = (
            select(LocationModel)
            .where(
                LocationModel.home_id == home_ctx.home_id,
                LocationModel.deleted_at.is_(None),
                or_(
                    LocationModel.name.ilike(term),
                    LocationModel.path.ilike(term),
                    LocationModel.description.ilike(term)
                )
            )
            .limit(limit_per_domain)
        )
        loc_items = (await db.execute(loc_q)).scalars().all()
        for l in loc_items:
            results.append(
                SearchResultItemDTO(
                    id=l.id,
                    domain="LOCATION",
                    title=l.name,
                    subtitle=f"Path: {l.path} • Type: {l.location_type}",
                    location_path=l.path,
                    status="ACTIVE",
                    relevance=0.8,
                    navigation_target=f"/locations/{l.id}"
                )
            )
        domain_counts["LOCATION"] = len(loc_items)

    # 4. Search Purchase List Items
    if not domain or domain == "PURCHASE":
        shop_q = (
            select(PurchaseItemModel)
            .where(
                PurchaseItemModel.home_id == home_ctx.home_id,
                or_(
                    PurchaseItemModel.name.ilike(term),
                    PurchaseItemModel.notes.ilike(term)
                )
            )
            .limit(limit_per_domain)
        )
        shop_items = (await db.execute(shop_q)).scalars().all()
        for s in shop_items:
            check_str = "Purchased" if s.is_checked else "To Buy"
            results.append(
                SearchResultItemDTO(
                    id=s.id,
                    domain="PURCHASE",
                    title=s.name,
                    subtitle=f"{s.quantity} {s.unit} • Priority: {s.priority}",
                    status=check_str,
                    relevance=0.7,
                    navigation_target="/purchase-list",
                    meta_info={"is_checked": s.is_checked, "priority": s.priority}
                )
            )
        domain_counts["PURCHASE"] = len(shop_items)

    # 5. Search Tasks & Responsibilities
    if not domain or domain == "TASK":
        task_q = (
            select(TaskModel)
            .options(selectinload(TaskModel.assignee))
            .where(
                TaskModel.home_id == home_ctx.home_id,
                TaskModel.deleted_at.is_(None),
                or_(
                    TaskModel.title.ilike(term),
                    TaskModel.description.ilike(term)
                )
            )
            .limit(limit_per_domain)
        )
        task_items = (await db.execute(task_q)).scalars().all()
        for t in task_items:
            due_str = f" • Due: {t.due_date}" if t.due_date else ""
            assignee_str = f" • Assigned: {t.assignee.profile.display_name}" if t.assignee and t.assignee.profile else ""
            results.append(
                SearchResultItemDTO(
                    id=t.id,
                    domain="TASK",
                    title=t.title,
                    subtitle=f"Status: {t.status}{due_str}{assignee_str}",
                    status=t.status,
                    relevance=0.7,
                    navigation_target=f"/tasks/{t.id}",
                    meta_info={"priority": t.priority, "due_date": t.due_date.isoformat() if t.due_date else None}
                )
            )
        domain_counts["TASK"] = len(task_items)

    # 6. Search Bills & Financial Records
    if not domain or domain == "BILL":
        bill_q = (
            select(BillModel)
            .where(
                BillModel.home_id == home_ctx.home_id,
                BillModel.deleted_at.is_(None),
                or_(
                    BillModel.title.ilike(term),
                    BillModel.notes.ilike(term)
                )
            )
            .limit(limit_per_domain)
        )
        bill_items = (await db.execute(bill_q)).scalars().all()
        for b in bill_items:
            results.append(
                SearchResultItemDTO(
                    id=b.id,
                    domain="BILL",
                    title=b.title,
                    subtitle=f"{b.currency} {b.expected_amount:.2f} • Due: {b.due_date} • {b.status}",
                    status=b.status,
                    relevance=0.7,
                    navigation_target=f"/bills/{b.id}",
                    meta_info={"amount": str(b.expected_amount), "currency": b.currency, "due_date": b.due_date.isoformat()}
                )
            )
        domain_counts["BILL"] = len(bill_items)

    # 7. Search Calendar Events
    if not domain or domain == "EVENT":
        event_q = (
            select(EventModel)
            .where(
                EventModel.home_id == home_ctx.home_id,
                EventModel.deleted_at.is_(None),
                or_(
                    EventModel.title.ilike(term),
                    EventModel.location.ilike(term),
                    EventModel.description.ilike(term)
                )
            )
            .limit(limit_per_domain)
        )
        event_items = (await db.execute(event_q)).scalars().all()
        for e in event_items:
            time_str = e.start_time.strftime("%d %b %Y")
            loc_str = f" • Location: {e.location}" if e.location else ""
            results.append(
                SearchResultItemDTO(
                    id=e.id,
                    domain="EVENT",
                    title=e.title,
                    subtitle=f"Date: {time_str}{loc_str}",
                    status=e.status,
                    relevance=0.6,
                    navigation_target=f"/calendar/{e.id}",
                    meta_info={"start_time": e.start_time.isoformat(), "is_all_day": e.is_all_day}
                )
            )
        domain_counts["EVENT"] = len(event_items)

    # 8. Search Home Members
    if not domain or domain == "MEMBER":
        mem_q = (
            select(HomeMemberModel)
            .options(selectinload(HomeMemberModel.user).selectinload(UserModel.profile))
            .where(
                HomeMemberModel.home_id == home_ctx.home_id,
                HomeMemberModel.status == "ACTIVE"
            )
        )
        members = (await db.execute(mem_q)).scalars().all()
        matching_members = []
        for m in members:
            u = m.user
            p_name = u.profile.display_name if (u and u.profile) else ""
            email = u.email if u else ""
            if query_clean.lower() in p_name.lower() or query_clean.lower() in email.lower():
                matching_members.append(
                    SearchResultItemDTO(
                        id=m.user_id,
                        domain="MEMBER",
                        title=p_name or email,
                        subtitle=f"Role: {m.role} • {email}",
                        status="ACTIVE",
                        relevance=0.5,
                        navigation_target="/settings/members",
                        meta_info={"email": email, "role": m.role}
                    )
                )
        results.extend(matching_members[:limit_per_domain])
        domain_counts["MEMBER"] = len(matching_members)

    # Sort results by relevance descending
    results.sort(key=lambda x: x.relevance, reverse=True)

    return ApiSuccessResponse(
        data=UnifiedSearchResponse(
            query=query_clean,
            total_results=len(results),
            results_by_domain=domain_counts,
            items=results
        )
    )
