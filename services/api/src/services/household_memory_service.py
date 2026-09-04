import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models import (
    AuditLogModel,
    HouseholdMemoryModel,
    UserPersonalizationPreferenceModel,
)
from src.schemas.intelligence_memory import (
    HouseholdMemoryCreateRequest,
    HouseholdMemoryResponseDTO,
    HouseholdMemoryUpdateRequest,
    MemoryCategory,
    MemorySource,
    MemoryStatus,
)


class HouseholdMemoryService:
    """
    Deterministic Household Memory Engine.
    Provides long-term memory retrieval, conflict resolution, deduplication, and privacy isolation.
    """

    @classmethod
    def _map_to_dto(cls, mem: HouseholdMemoryModel) -> HouseholdMemoryResponseDTO:
        return HouseholdMemoryResponseDTO(
            id=str(mem.id),
            home_id=str(mem.home_id),
            user_id=str(mem.user_id) if mem.user_id else None,
            category=MemoryCategory(mem.category),
            content=mem.content,
            source=MemorySource(mem.source),
            confidence=float(mem.confidence) if mem.confidence is not None else 1.0,
            status=MemoryStatus(mem.status),
            context_metadata=mem.context_metadata or {},
            last_used_at=mem.last_used_at,
            expires_at=mem.expires_at,
            created_at=mem.created_at or datetime.now(timezone.utc),
            updated_at=mem.updated_at or datetime.now(timezone.utc),
        )

    @classmethod
    async def create_memory(
        cls,
        db: AsyncSession,
        home_id: UUID,
        request: HouseholdMemoryCreateRequest,
        user_id: Optional[UUID] = None,
    ) -> HouseholdMemoryResponseDTO:
        """
        Creates or merges a household memory with duplicate prevention and conflict detection.
        """
        now = datetime.now(timezone.utc)
        normalized_content = request.content.strip().lower()

        # Duplicate check: check if an identical active memory already exists in this home
        stmt = select(HouseholdMemoryModel).where(
            HouseholdMemoryModel.home_id == home_id,
            HouseholdMemoryModel.category == request.category.value,
            HouseholdMemoryModel.status == MemoryStatus.ACTIVE.value,
            HouseholdMemoryModel.deleted_at.is_(None),
        )
        existing_memories = (await db.execute(stmt)).scalars().all()

        for existing in existing_memories:
            if existing.content.strip().lower() == normalized_content:
                # Update confidence and timestamp if new source is user-provided
                if request.source in [MemorySource.USER_PROVIDED, MemorySource.USER_CONFIRMED]:
                    existing.source = request.source.value
                    existing.confidence = Decimal(str(request.confidence))
                    existing.updated_at = now
                    await db.commit()
                    await db.refresh(existing)
                return cls._map_to_dto(existing)

        # Conflict resolution / superseding:
        # If user explicitly provides a new preference in the same category, update previous conflicting AI-inferred ones
        if request.source in [MemorySource.USER_PROVIDED, MemorySource.USER_CONFIRMED]:
            for existing in existing_memories:
                if existing.source == MemorySource.AI_INFERRED.value:
                    existing.status = MemoryStatus.ARCHIVED.value
                    existing.updated_at = now

        new_mem = HouseholdMemoryModel(
            id=uuid4(),
            home_id=home_id,
            user_id=user_id,
            category=request.category.value,
            content=request.content.strip(),
            source=request.source.value,
            confidence=Decimal(str(request.confidence)),
            status=MemoryStatus.ACTIVE.value,
            context_metadata=request.context_metadata or {},
            expires_at=request.expires_at,
            created_at=now,
            updated_at=now,
        )
        db.add(new_mem)

        # Audit log
        audit = AuditLogModel(
            id=uuid4(),
            entity_type="HOUSEHOLD_MEMORY",
            entity_id=new_mem.id,
            action="MEMORY_CREATED",
            performed_by=user_id,
            details=json.dumps({"category": new_mem.category, "source": new_mem.source}),
        )
        db.add(audit)
        await db.commit()
        await db.refresh(new_mem)

        return cls._map_to_dto(new_mem)

    @classmethod
    async def list_memories(
        cls,
        db: AsyncSession,
        home_id: UUID,
        category: Optional[MemoryCategory] = None,
        status: Optional[MemoryStatus] = None,
        user_id: Optional[UUID] = None,
        include_household: bool = True,
    ) -> List[HouseholdMemoryResponseDTO]:
        """
        Lists memories with home isolation and optional user filtering.
        """
        stmt = select(HouseholdMemoryModel).where(
            HouseholdMemoryModel.home_id == home_id,
            HouseholdMemoryModel.deleted_at.is_(None),
        )

        if category:
            stmt = stmt.where(HouseholdMemoryModel.category == category.value)

        if status:
            stmt = stmt.where(HouseholdMemoryModel.status == status.value)
        else:
            stmt = stmt.where(HouseholdMemoryModel.status == MemoryStatus.ACTIVE.value)

        if user_id and not include_household:
            stmt = stmt.where(HouseholdMemoryModel.user_id == user_id)
        elif user_id and include_household:
            stmt = stmt.where(
                or_(
                    HouseholdMemoryModel.user_id == user_id,
                    HouseholdMemoryModel.user_id.is_(None),
                )
            )

        stmt = stmt.order_by(HouseholdMemoryModel.created_at.desc())
        memories = (await db.execute(stmt)).scalars().all()
        return [cls._map_to_dto(m) for m in memories]

    @classmethod
    async def update_memory(
        cls,
        db: AsyncSession,
        home_id: UUID,
        memory_id: UUID,
        request: HouseholdMemoryUpdateRequest,
        user_id: Optional[UUID] = None,
    ) -> Optional[HouseholdMemoryResponseDTO]:
        """
        Updates memory content, category, or status.
        """
        stmt = select(HouseholdMemoryModel).where(
            HouseholdMemoryModel.id == memory_id,
            HouseholdMemoryModel.home_id == home_id,
            HouseholdMemoryModel.deleted_at.is_(None),
        )
        mem = (await db.execute(stmt)).scalar_one_or_none()
        if not mem:
            return None

        if request.content is not None:
            mem.content = request.content.strip()
            mem.source = MemorySource.USER_CONFIRMED.value
        if request.category is not None:
            mem.category = request.category.value
        if request.status is not None:
            mem.status = request.status.value
        if request.confidence is not None:
            mem.confidence = Decimal(str(request.confidence))
        if request.context_metadata is not None:
            mem.context_metadata = request.context_metadata
        if request.expires_at is not None:
            mem.expires_at = request.expires_at

        mem.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(mem)
        return cls._map_to_dto(mem)

    @classmethod
    async def delete_memory(
        cls,
        db: AsyncSession,
        home_id: UUID,
        memory_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> bool:
        """
        Soft deletes a memory item.
        """
        stmt = select(HouseholdMemoryModel).where(
            HouseholdMemoryModel.id == memory_id,
            HouseholdMemoryModel.home_id == home_id,
            HouseholdMemoryModel.deleted_at.is_(None),
        )
        mem = (await db.execute(stmt)).scalar_one_or_none()
        if not mem:
            return False

        mem.deleted_at = datetime.now(timezone.utc)
        mem.status = MemoryStatus.ARCHIVED.value
        await db.commit()
        return True

    @classmethod
    async def retrieve_relevant_memories(
        cls,
        db: AsyncSession,
        home_id: UUID,
        query: str,
        user_id: Optional[UUID] = None,
        limit: int = 5,
    ) -> List[str]:
        """
        Deterministic, relevance-filtered memory retrieval for AI context assembly.
        Respects personalization and AI memory enable/disable toggle.
        """
        if user_id:
            pref_stmt = select(UserPersonalizationPreferenceModel).where(
                UserPersonalizationPreferenceModel.user_id == user_id,
                UserPersonalizationPreferenceModel.home_id == home_id,
            )
            pref = (await db.execute(pref_stmt)).scalar_one_or_none()
            if pref and not pref.ai_memory_enabled:
                return []

        # Retrieve active memories for this home and user
        stmt = select(HouseholdMemoryModel).where(
            HouseholdMemoryModel.home_id == home_id,
            HouseholdMemoryModel.status == MemoryStatus.ACTIVE.value,
            HouseholdMemoryModel.deleted_at.is_(None),
        )
        if user_id:
            stmt = stmt.where(
                or_(
                    HouseholdMemoryModel.user_id == user_id,
                    HouseholdMemoryModel.user_id.is_(None),
                )
            )

        all_memories = (await db.execute(stmt)).scalars().all()
        if not all_memories:
            return []

        # Simple deterministic keyword & category relevance scoring
        words = set(w.lower() for w in query.split() if len(w) > 2)
        scored: List[tuple[float, HouseholdMemoryModel]] = []

        now = datetime.now(timezone.utc)
        for m in all_memories:
            score = float(m.confidence) * 1.0
            content_lower = m.content.lower()

            # Word match boost
            matches = sum(1 for w in words if w in content_lower)
            score += matches * 2.5

            # User preference boost
            if m.category in [MemoryCategory.PREFERENCE.value, MemoryCategory.USER_INSTRUCTION.value]:
                score += 1.5

            if m.source in [MemorySource.USER_PROVIDED.value, MemorySource.USER_CONFIRMED.value]:
                score += 1.0

            scored.append((score, m))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_memories = [m for _, m in scored[:limit]]

        # Update last_used_at
        for m in top_memories:
            m.last_used_at = now
        await db.commit()

        return [f"[{m.category}] {m.content}" for m in top_memories]
