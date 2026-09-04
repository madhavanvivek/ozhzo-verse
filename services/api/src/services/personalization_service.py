from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models import (
    AutomationExecutionModel,
    BillModel,
    HomeModel,
    InventoryItemModel,
    PurchaseItemModel,
    TaskModel,
    UserPersonalizationPreferenceModel,
)

from src.schemas.intelligence_memory import (
    HouseholdDigestDTO,
    PersonalizationPreferenceDTO,
    PersonalizationPreferenceUpdateRequest,
)


class PersonalizationService:
    """
    Manages user personalization preferences and generates weekly household intelligence digests.
    """

    @classmethod
    def _map_pref_to_dto(cls, p: UserPersonalizationPreferenceModel) -> PersonalizationPreferenceDTO:
        return PersonalizationPreferenceDTO(
            id=str(p.id),
            user_id=str(p.user_id),
            home_id=str(p.home_id),
            personalization_enabled=bool(p.personalization_enabled) if p.personalization_enabled is not None else True,
            ai_memory_enabled=bool(p.ai_memory_enabled) if p.ai_memory_enabled is not None else True,
            reminder_timing_preference=str(p.reminder_timing_preference or "1_DAY_BEFORE"),
            recommendation_frequency=str(p.recommendation_frequency or "BALANCED"),
            digest_enabled=bool(p.digest_enabled) if p.digest_enabled is not None else True,
            digest_day_of_week=str(p.digest_day_of_week or "SUNDAY"),
            preferences_json=p.preferences_json if isinstance(p.preferences_json, dict) else {},
            updated_at=p.updated_at if isinstance(p.updated_at, datetime) else datetime.now(timezone.utc),
        )


    @classmethod
    async def get_or_create_preferences(
        cls,
        db: AsyncSession,
        user_id: UUID,
        home_id: UUID,
    ) -> PersonalizationPreferenceDTO:
        stmt = select(UserPersonalizationPreferenceModel).where(
            UserPersonalizationPreferenceModel.user_id == user_id,
            UserPersonalizationPreferenceModel.home_id == home_id,
        )
        pref = (await db.execute(stmt)).scalar_one_or_none()
        if not pref:
            pref = UserPersonalizationPreferenceModel(
                id=uuid4(),
                user_id=user_id,
                home_id=home_id,
                personalization_enabled=True,
                ai_memory_enabled=True,
                reminder_timing_preference="1_DAY_BEFORE",
                recommendation_frequency="BALANCED",
                digest_enabled=True,
                digest_day_of_week="SUNDAY",
                preferences_json={},
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            db.add(pref)
            await db.commit()
            await db.refresh(pref)

        return cls._map_pref_to_dto(pref)

    @classmethod
    async def update_preferences(
        cls,
        db: AsyncSession,
        user_id: UUID,
        home_id: UUID,
        request: PersonalizationPreferenceUpdateRequest,
    ) -> PersonalizationPreferenceDTO:
        stmt = select(UserPersonalizationPreferenceModel).where(
            UserPersonalizationPreferenceModel.user_id == user_id,
            UserPersonalizationPreferenceModel.home_id == home_id,
        )
        pref = (await db.execute(stmt)).scalar_one_or_none()
        now = datetime.now(timezone.utc)

        if not pref:
            pref = UserPersonalizationPreferenceModel(
                id=uuid4(),
                user_id=user_id,
                home_id=home_id,
                personalization_enabled=request.personalization_enabled if request.personalization_enabled is not None else True,
                ai_memory_enabled=request.ai_memory_enabled if request.ai_memory_enabled is not None else True,
                reminder_timing_preference=request.reminder_timing_preference or "1_DAY_BEFORE",
                recommendation_frequency=request.recommendation_frequency or "BALANCED",
                digest_enabled=request.digest_enabled if request.digest_enabled is not None else True,
                digest_day_of_week=request.digest_day_of_week or "SUNDAY",
                preferences_json=request.preferences_json or {},
                created_at=now,
                updated_at=now,
            )
            db.add(pref)
        else:
            if request.personalization_enabled is not None:
                pref.personalization_enabled = request.personalization_enabled
            if request.ai_memory_enabled is not None:
                pref.ai_memory_enabled = request.ai_memory_enabled
            if request.reminder_timing_preference is not None:
                pref.reminder_timing_preference = request.reminder_timing_preference
            if request.recommendation_frequency is not None:
                pref.recommendation_frequency = request.recommendation_frequency
            if request.digest_enabled is not None:
                pref.digest_enabled = request.digest_enabled
            if request.digest_day_of_week is not None:
                pref.digest_day_of_week = request.digest_day_of_week
            if request.preferences_json is not None:
                pref.preferences_json = request.preferences_json
            pref.updated_at = now

        await db.commit()
        await db.refresh(pref)
        return cls._map_pref_to_dto(pref)

    @classmethod
    async def generate_weekly_digest(
        cls,
        db: AsyncSession,
        home_id: UUID,
    ) -> HouseholdDigestDTO:
        """
        Generates an intelligent weekly summary of household activity and metrics.
        """
        now = datetime.now(timezone.utc)
        today = now.date()
        week_ago = now - timedelta(days=7)
        week_ahead = today + timedelta(days=7)

        # Home name
        home_stmt = select(HomeModel).where(HomeModel.id == home_id)
        home = (await db.execute(home_stmt)).scalar_one_or_none()
        home_name = home.name if home else "Household"

        # 1. Tasks
        completed_tasks_stmt = select(func.count(TaskModel.id)).where(
            TaskModel.home_id == home_id,
            TaskModel.status == "COMPLETED",
            TaskModel.updated_at >= week_ago,
        )
        completed_tasks_count = (await db.execute(completed_tasks_stmt)).scalar() or 0

        overdue_tasks_stmt = select(func.count(TaskModel.id)).where(
            TaskModel.home_id == home_id,
            TaskModel.status.in_(["TODO", "IN_PROGRESS"]),
            TaskModel.due_date < today,
            TaskModel.deleted_at.is_(None),
        )
        overdue_tasks_count = (await db.execute(overdue_tasks_stmt)).scalar() or 0

        # 2. Bills
        paid_bills_stmt = select(func.count(BillModel.id)).where(
            BillModel.home_id == home_id,
            BillModel.status == "PAID",
            BillModel.updated_at >= week_ago,
        )
        paid_bills_count = (await db.execute(paid_bills_stmt)).scalar() or 0

        upcoming_bills_stmt = select(func.count(BillModel.id)).where(
            BillModel.home_id == home_id,
            BillModel.status.in_(["UNPAID", "UPCOMING"]),
            BillModel.due_date <= week_ahead,
            BillModel.due_date >= today,
            BillModel.deleted_at.is_(None),
        )
        upcoming_bills_count = (await db.execute(upcoming_bills_stmt)).scalar() or 0

        # 3. Shopping & Inventory
        purchased_items_stmt = select(func.count(PurchaseItemModel.id)).where(
            PurchaseItemModel.home_id == home_id,
            PurchaseItemModel.status == "PURCHASED",
            PurchaseItemModel.updated_at >= week_ago,
        )
        purchased_count = (await db.execute(purchased_items_stmt)).scalar() or 0


        low_inv_stmt = select(func.count(InventoryItemModel.id)).where(
            InventoryItemModel.home_id == home_id,
            InventoryItemModel.deleted_at.is_(None),
            InventoryItemModel.quantity <= InventoryItemModel.min_threshold,
        )
        low_inv_count = (await db.execute(low_inv_stmt)).scalar() or 0

        # 4. Automations
        auto_exec_stmt = select(func.count(AutomationExecutionModel.id)).where(
            AutomationExecutionModel.home_id == home_id,
            AutomationExecutionModel.created_at >= week_ago,
        )
        automations_count = (await db.execute(auto_exec_stmt)).scalar() or 0

        highlights = []
        if completed_tasks_count > 0:
            highlights.append(f"{completed_tasks_count} chores and household tasks completed.")
        if paid_bills_count > 0:
            highlights.append(f"{paid_bills_count} bills settled successfully.")
        if purchased_count > 0:
            highlights.append(f"{purchased_count} grocery & household items purchased.")
        if automations_count > 0:
            highlights.append(f"{automations_count} automated rules executed smoothly.")

        key_recommendations = []
        if overdue_tasks_count > 0:
            key_recommendations.append(f"Catch up on {overdue_tasks_count} pending overdue tasks.")
        if upcoming_bills_count > 0:
            key_recommendations.append(f"{upcoming_bills_count} bills approaching due date in the next 7 days.")
        if low_inv_count > 0:
            key_recommendations.append(f"{low_inv_count} pantry consumables are running low on stock.")

        if not highlights:
            highlights.append("Household routine running smoothly with no major disruptions.")

        return HouseholdDigestDTO(
            home_id=str(home_id),
            home_name=home_name,
            period_start=week_ago,
            period_end=now,
            tasks_completed_count=completed_tasks_count,
            tasks_overdue_count=overdue_tasks_count,
            bills_paid_count=paid_bills_count,
            bills_upcoming_count=upcoming_bills_count,
            shopping_items_purchased_count=purchased_count,
            inventory_low_count=low_inv_count,
            automations_executed_count=automations_count,
            highlights=highlights,
            key_recommendations=key_recommendations,
        )
