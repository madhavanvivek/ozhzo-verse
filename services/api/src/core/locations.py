from typing import Dict, List, Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models import LocationModel
from src.schemas.inventory import LocationDTO, LocationTreeDTO


async def build_location_path_map(db: AsyncSession, home_id: UUID) -> Dict[UUID, str]:
    """
    Fetches all active locations for a Home and computes their full path string.
    Returns a dictionary mapping location_id to 'Path > String'.
    """
    query = select(LocationModel).where(
        LocationModel.home_id == home_id,
        LocationModel.deleted_at == None
    )
    result = await db.execute(query)
    locations = result.scalars().all()

    loc_dict = {loc.id: loc for loc in locations if hasattr(loc, "id")}
    path_map: Dict[UUID, str] = {}

    def get_path(loc_id: UUID, visited: set) -> str:
        if loc_id in path_map:
            return path_map[loc_id]
        if loc_id in visited:
            return loc_dict[loc_id].name  # Break circular reference if any
        visited.add(loc_id)

        loc = loc_dict.get(loc_id)
        if not loc:
            return ""

        if loc.parent_id and loc.parent_id in loc_dict:
            parent_path = get_path(loc.parent_id, visited)
            full_path = f"{parent_path} > {loc.name}" if parent_path else loc.name
        else:
            full_path = loc.name

        path_map[loc_id] = full_path
        return full_path

    for loc in locations:
        if hasattr(loc, "id"):
            get_path(loc.id, set())

    return path_map


async def get_location_path_for_id(db: AsyncSession, location_id: UUID, home_id: UUID) -> Optional[str]:
    path_map = await build_location_path_map(db, home_id)
    return path_map.get(location_id)


def build_location_tree(locations: List[LocationModel], path_map: Dict[UUID, str]) -> List[LocationTreeDTO]:
    """Constructs a nested LocationTreeDTO list from flat LocationModel list."""
    nodes: Dict[UUID, LocationTreeDTO] = {}
    roots: List[LocationTreeDTO] = []

    for loc in locations:
        nodes[loc.id] = LocationTreeDTO(
            id=loc.id,
            home_id=loc.home_id,
            parent_id=loc.parent_id,
            name=loc.name,
            location_type=loc.location_type,
            description=loc.description,
            icon=loc.icon,
            sort_order=loc.sort_order,
            is_active=loc.is_active,
            path=path_map.get(loc.id, loc.name),
            item_count=len(loc.items) if loc.items else 0,
            created_at=loc.created_at,
            updated_at=loc.updated_at,
            children=[]
        )

    for loc in locations:
        node = nodes[loc.id]
        if loc.parent_id and loc.parent_id in nodes:
            nodes[loc.parent_id].children.append(node)
        else:
            roots.append(node)

    return roots
