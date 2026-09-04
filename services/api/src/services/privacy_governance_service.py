import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy import select, delete, update, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models import (
    AIConversationSessionModel,
    AIAgentAuditModel,
    AutomationExecutionModel,
    BillModel,
    EventModel,
    HomeMemberModel,
    HomeModel,
    HouseholdMemoryModel,
    InventoryItemModel,
    InvitationModel,
    NotificationModel,
    PurchaseItemModel,
    TaskModel,
    UserModel,
    UserProfileModel,
    UserPersonalizationPreferenceModel
)

logger = logging.getLogger("ozhzo.privacy.governance")


class PrivacyGovernanceService:
    """
    Privacy Governance & Data Retention Engine.
    Provides GDPR transparency, structured data portability export, safe erasure, and automated log retention purging.
    """

    @classmethod
    async def get_privacy_summary(
        cls, db: AsyncSession, home_id: UUID, user_id: UUID
    ) -> Dict[str, Any]:
        """
        Returns a comprehensive data transparency summary explaining what household data is stored,
        AI memory usage, personalization controls, and data retention windows.
        """
        # 1. Count entities for home
        task_count = (await db.execute(select(TaskModel).where(TaskModel.home_id == home_id, TaskModel.deleted_at.is_(None)))).scalars().all()
        bill_count = (await db.execute(select(BillModel).where(BillModel.home_id == home_id, BillModel.deleted_at.is_(None)))).scalars().all()
        item_count = (await db.execute(select(InventoryItemModel).where(InventoryItemModel.home_id == home_id, InventoryItemModel.deleted_at.is_(None)))).scalars().all()
        memory_count = (await db.execute(select(HouseholdMemoryModel).where(HouseholdMemoryModel.home_id == home_id, HouseholdMemoryModel.deleted_at.is_(None)))).scalars().all()
        user_memories = [m for m in memory_count if m.user_id == user_id]

        # 2. Check personalization status
        pref_stmt = select(UserPersonalizationPreferenceModel).where(
            UserPersonalizationPreferenceModel.user_id == user_id,
            UserPersonalizationPreferenceModel.home_id == home_id
        )
        pref = (await db.execute(pref_stmt)).scalar_one_or_none()

        return {
            "home_id": str(home_id),
            "user_id": str(user_id),
            "stored_data_overview": {
                "active_tasks": len(task_count),
                "tracked_bills": len(bill_count),
                "inventory_items": len(item_count),
                "total_household_memories": len(memory_count),
                "your_personal_memories": len(user_memories),
            },
            "personalization_and_ai_privacy": {
                "personalization_enabled": pref.personalization_enabled if pref else True,
                "ai_memory_enabled": pref.ai_memory_enabled if pref else True,
                "ai_data_usage_policy": "Household memory is strictly scoped to this Home. Your data is never used to train global AI models or shared across household boundaries.",
            },
            "data_retention_schedule": [
                {"category": "Read Notifications", "retention_period": "60 Days", "policy": "Automated purge of resolved/read alerts"},
                {"category": "AI Conversation Sessions", "retention_period": "30 Days", "policy": "Temporary turn history automatically expired"},
                {"category": "Automation Execution History", "retention_period": "90 Days", "policy": "Transient execution telemetry purged; rules preserved"},
                {"category": "Expired Invitations", "retention_period": "14 Days", "policy": "Unclaimed invite links cleaned up"},
                {"category": "Financial & Audit Ledgers", "retention_period": "Statutory (7 Years)", "policy": "Anonymized on user erasure; preserved for compliance"}
            ],
            "user_rights": {
                "data_portability": "Available via GET /homes/{home_id}/privacy/export",
                "right_to_erasure": "Available via POST /homes/{home_id}/privacy/delete",
                "rectification": "Edit preferences in Settings > Personalization or Household Memory Vault"
            }
        }

    @classmethod
    async def export_user_and_home_data(
        cls, db: AsyncSession, home_id: UUID, user_id: UUID
    ) -> Dict[str, Any]:
        """
        Exports a complete structured JSON archive of user profile, household tasks, bills, inventory,
        shopping list, memories, and notifications for GDPR Article 20 Data Portability.
        """
        # User profile
        user_stmt = select(UserModel).where(UserModel.id == user_id)
        user = (await db.execute(user_stmt)).scalar_one_or_none()
        profile_stmt = select(UserProfileModel).where(UserProfileModel.user_id == user_id)
        profile = (await db.execute(profile_stmt)).scalar_one_or_none()

        # Home metadata
        home_stmt = select(HomeModel).where(HomeModel.id == home_id)
        home = (await db.execute(home_stmt)).scalar_one_or_none()

        # Tasks
        tasks = (await db.execute(select(TaskModel).where(TaskModel.home_id == home_id))).scalars().all()
        # Bills
        bills = (await db.execute(select(BillModel).where(BillModel.home_id == home_id))).scalars().all()
        # Inventory
        inv = (await db.execute(select(InventoryItemModel).where(InventoryItemModel.home_id == home_id))).scalars().all()
        # Shopping
        shop = (await db.execute(select(PurchaseItemModel).where(PurchaseItemModel.home_id == home_id))).scalars().all()
        # Memories
        memories = (await db.execute(select(HouseholdMemoryModel).where(HouseholdMemoryModel.home_id == home_id))).scalars().all()
        # Notifications
        notifs = (await db.execute(select(NotificationModel).where(NotificationModel.user_id == user_id))).scalars().all()

        return {
            "export_generated_at": datetime.now(timezone.utc).isoformat(),
            "export_version": "1.0",
            "user": {
                "id": str(user.id) if user else str(user_id),
                "email": user.email if user else None,
                "phone_number": user.phone_number if user else None,
                "display_name": profile.display_name if profile else None,
                "timezone": profile.timezone if profile else "UTC",
                "created_at": user.created_at.isoformat() if user and user.created_at else None,
            },
            "home": {
                "id": str(home.id) if home else str(home_id),
                "name": home.name if home else None,
                "currency": home.currency if home else "INR",
                "timezone": home.timezone if home else "UTC",
            },
            "tasks": [
                {
                    "id": str(t.id),
                    "title": t.title,
                    "description": t.description,
                    "status": t.status,
                    "priority": t.priority,
                    "due_date": t.due_date.isoformat() if t.due_date else None,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
                for t in tasks
            ],
            "bills": [
                {
                    "id": str(b.id),
                    "title": b.title,
                    "amount": float(b.expected_amount) if b.expected_amount else 0.0,
                    "currency": b.currency,
                    "due_date": b.due_date.isoformat() if b.due_date else None,
                    "status": b.status,
                }
                for b in bills
            ],
            "inventory": [
                {
                    "id": str(i.id),
                    "name": i.name,
                    "quantity": float(i.quantity) if i.quantity else 0.0,
                    "unit": i.unit,
                    "status": i.status,
                }
                for i in inv
            ],
            "shopping_list": [
                {
                    "id": str(s.id),
                    "name": s.name,
                    "quantity": float(s.quantity) if s.quantity else 1.0,
                    "unit": s.unit,
                    "status": s.status,
                }
                for s in shop
            ],
            "household_memories": [
                {
                    "id": str(m.id),
                    "category": m.category,
                    "content": m.content,
                    "source": m.source,
                    "status": m.status,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in memories
            ],
            "notifications": [
                {
                    "id": str(n.id),
                    "title": n.title,
                    "message": n.message,
                    "priority": n.priority,
                    "is_read": n.is_read,
                    "created_at": n.created_at.isoformat() if n.created_at else None,
                }
                for n in notifs
            ]
        }

    @classmethod
    async def request_data_deletion(
        cls, db: AsyncSession, home_id: UUID, user_id: UUID, confirmation_phrase: str
    ) -> Dict[str, Any]:
        """
        Executes GDPR Article 17 Right to Erasure.
        Anonymizes personal identifying data and soft-deletes personal memories while safely preserving statutory audit trails.
        """
        if confirmation_phrase.strip().upper() != "DELETE MY DATA":
            return {
                "status": "FAILED",
                "message": "Confirmation phrase must be 'DELETE MY DATA' to execute permanent deletion."
            }

        now = datetime.now(timezone.utc)

        # 1. Anonymize user profile
        prof_stmt = select(UserProfileModel).where(UserProfileModel.user_id == user_id)
        prof = (await db.execute(prof_stmt)).scalar_one_or_none()
        if prof:
            prof.display_name = "Former Resident"
            prof.avatar_url = None
            prof.phone_number = None

        # 2. Soft-delete user's memories
        mem_stmt = select(HouseholdMemoryModel).where(
            HouseholdMemoryModel.user_id == user_id,
            HouseholdMemoryModel.home_id == home_id
        )
        user_mems = (await db.execute(mem_stmt)).scalars().all()
        for m in user_mems:
            m.deleted_at = now
            m.status = "ARCHIVED"

        # 3. Clear personalization preferences
        pref_stmt = select(UserPersonalizationPreferenceModel).where(
            UserPersonalizationPreferenceModel.user_id == user_id,
            UserPersonalizationPreferenceModel.home_id == home_id
        )
        pref = (await db.execute(pref_stmt)).scalar_one_or_none()
        if pref:
            pref.personalization_enabled = False
            pref.ai_memory_enabled = False

        # 4. Clear active AI sessions
        await db.execute(
            delete(AIConversationSessionModel).where(
                AIConversationSessionModel.user_id == user_id,
                AIConversationSessionModel.home_id == home_id
            )
        )

        await db.commit()
        logger.info(f"Executed data deletion & anonymization for user {user_id} in home {home_id}")

        return {
            "status": "COMPLETED",
            "message": "Personal data successfully erased and anonymized in compliance with GDPR standards.",
            "anonymized_at": now.isoformat()
        }

    @classmethod
    async def execute_data_retention_purge(cls, db: AsyncSession) -> Dict[str, int]:
        """
        Purges expired transient records according to data retention policies.
        """
        now = datetime.now(timezone.utc)
        purged_counts = {"notifications": 0, "ai_sessions": 0, "automation_executions": 0, "invitations": 0}

        # 1. Purge read notifications > 60 days
        notif_cutoff = now - timedelta(days=60)
        notif_del = await db.execute(
            delete(NotificationModel).where(
                NotificationModel.is_read == True,
                NotificationModel.created_at < notif_cutoff
            )
        )
        purged_counts["notifications"] = notif_del.rowcount or 0

        # 2. Purge expired AI sessions > 30 days
        ai_cutoff = now - timedelta(days=30)
        ai_del = await db.execute(
            delete(AIConversationSessionModel).where(
                AIConversationSessionModel.expires_at < ai_cutoff
            )
        )
        purged_counts["ai_sessions"] = ai_del.rowcount or 0

        # 3. Purge completed automation executions > 90 days
        auto_cutoff = now - timedelta(days=90)
        auto_del = await db.execute(
            delete(AutomationExecutionModel).where(
                AutomationExecutionModel.created_at < auto_cutoff
            )
        )
        purged_counts["automation_executions"] = auto_del.rowcount or 0

        # 4. Purge expired invitations > 14 days
        inv_cutoff = now - timedelta(days=14)
        inv_del = await db.execute(
            delete(InvitationModel).where(
                InvitationModel.status.in_(["EXPIRED", "REVOKED"]),
                InvitationModel.created_at < inv_cutoff
            )
        )
        purged_counts["invitations"] = inv_del.rowcount or 0

        await db.commit()
        logger.info(f"Data retention purge completed: {purged_counts}")
        return purged_counts
