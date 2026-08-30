import uuid
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.infrastructure.database.session import Base


def utc_now():
    return datetime.now(timezone.utc)


class UserModel(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone_number = Column(String(32), unique=True, nullable=True, index=True)
    country_code = Column(String(8), nullable=True)
    email = Column(String(255), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    mobile_verified = Column(Boolean, default=False, nullable=False)
    is_super_admin = Column(Boolean, default=False, nullable=False)
    system_role = Column(String(32), default="USER", nullable=False)  # USER, SUPER_ADMIN, PLATFORM_ADMIN, SUPPORT_ADMIN, ANALYST
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    profile = relationship("UserProfileModel", back_populates="user", uselist=False, cascade="all, delete-orphan")
    memberships = relationship("HomeMemberModel", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("NotificationModel", back_populates="user", cascade="all, delete-orphan")


class UserProfileModel(Base):
    __tablename__ = "user_profiles"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    display_name = Column(String(100), nullable=False)
    phone_number = Column(String(32), nullable=True)
    country_code = Column(String(8), nullable=True)
    avatar_url = Column(String(512), nullable=True)
    timezone = Column(String(64), default="UTC", nullable=False)
    preferred_language = Column(String(10), default="en", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("UserModel", back_populates="profile")

    @property
    def first_name(self) -> str:
        parts = (self.display_name or "").strip().split(" ", 1)
        return parts[0] if parts else "Member"

    @property
    def last_name(self) -> str:
        parts = (self.display_name or "").strip().split(" ", 1)
        return parts[1] if len(parts) > 1 else ""


class OTPVerificationModel(Base):
    __tablename__ = "otp_verifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone_number = Column(String(32), nullable=False, index=True)
    otp_code_hash = Column(String(255), nullable=False)
    purpose = Column(String(32), default="REGISTRATION", nullable=False)  # REGISTRATION, LOGIN, INVITATION
    is_verified = Column(Boolean, default=False, nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class AuditLogModel(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type = Column(String(64), nullable=False)  # USER, HOME, HOME_MEMBER, INVITATION, ROLE
    entity_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    action = Column(String(64), nullable=False, index=True)
    performed_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class HomeModel(Base):
    __tablename__ = "homes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(120), nullable=False)
    country = Column(String(8), nullable=True)
    state_province = Column(String(64), nullable=True)
    district_city = Column(String(64), nullable=True)
    postal_code = Column(String(32), nullable=True)
    currency = Column(String(3), default="USD", nullable=False)
    timezone = Column(String(64), default="UTC", nullable=False)
    address = Column(Text, nullable=True)
    avatar_url = Column(String(512), nullable=True)
    status = Column(String(32), default="ACTIVE", nullable=False)  # ACTIVE, SUSPENDED
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    members = relationship("HomeMemberModel", back_populates="home", cascade="all, delete-orphan")
    invitations = relationship("InvitationModel", back_populates="home", cascade="all, delete-orphan")
    units = relationship("UnitModel", back_populates="home", cascade="all, delete-orphan")
    locations = relationship("LocationModel", back_populates="home", cascade="all, delete-orphan")
    inventory_items = relationship("InventoryItemModel", back_populates="home", cascade="all, delete-orphan")
    inventory_categories = relationship("InventoryCategoryModel", back_populates="home", cascade="all, delete-orphan")
    stock_movements = relationship("StockMovementModel", back_populates="home", cascade="all, delete-orphan")
    location_movements = relationship("LocationMovementModel", back_populates="home", cascade="all, delete-orphan")
    asset_loans = relationship("AssetLoanModel", back_populates="home", cascade="all, delete-orphan")
    purchase_items = relationship("PurchaseItemModel", back_populates="home", cascade="all, delete-orphan")
    purchase_history = relationship("PurchaseHistoryModel", back_populates="home", cascade="all, delete-orphan")
    task_categories = relationship("TaskCategoryModel", back_populates="home", cascade="all, delete-orphan")
    tasks = relationship("TaskModel", back_populates="home", cascade="all, delete-orphan")
    bill_categories = relationship("BillCategoryModel", back_populates="home", cascade="all, delete-orphan")
    bills = relationship("BillModel", back_populates="home", cascade="all, delete-orphan")
    bill_payments = relationship("BillPaymentModel", back_populates="home", cascade="all, delete-orphan")
    shopping_lists = relationship("ShoppingListModel", back_populates="home", cascade="all, delete-orphan")
    event_categories = relationship("EventCategoryModel", back_populates="home", cascade="all, delete-orphan")
    events = relationship("EventModel", back_populates="home", cascade="all, delete-orphan")
    subscription = relationship("SubscriptionModel", back_populates="home", uselist=False, cascade="all, delete-orphan")


class HomeMemberModel(Base):
    __tablename__ = "home_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    home_id = Column(UUID(as_uuid=True), ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(32), default="MEMBER", nullable=False)  # HOME_ADMIN, MEMBER, OWNER, ADMIN, CHILD, GUEST
    status = Column(String(32), default="ACTIVE", nullable=False)  # INVITED, PENDING_SUBSCRIPTION, ACTIVE, SUSPENDED, LEFT, REMOVED
    joined_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("home_id", "user_id", name="uq_home_members_home_user"),
        Index("idx_home_members_lookup", "home_id", "user_id", "status"),
    )

    home = relationship("HomeModel", back_populates="members")
    user = relationship("UserModel", back_populates="memberships")


class InvitationModel(Base):
    __tablename__ = "invitations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    home_id = Column(UUID(as_uuid=True), ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True)
    invited_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    phone_number = Column(String(32), nullable=True)
    email = Column(String(255), nullable=True)
    role = Column(String(32), default="MEMBER", nullable=False)  # HOME_ADMIN, MEMBER
    invitation_mode = Column(String(32), default="INVITE_ONLY", nullable=False)  # INVITE_ONLY, INVITE_WITH_SUBSCRIPTION
    token = Column(String(64), unique=True, nullable=False, index=True)
    invitation_code = Column(String(32), unique=True, nullable=True, index=True)
    status = Column(String(32), default="PENDING", nullable=False)  # PENDING, ACCEPTED, REVOKED, EXPIRED, DECLINED
    accepted_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    home = relationship("HomeModel", back_populates="invitations")

    def __init__(self, **kwargs):
        if "invite_token" in kwargs and "token" not in kwargs:
            kwargs["token"] = kwargs.pop("invite_token")
        super().__init__(**kwargs)

    @property
    def invite_token(self) -> str:
        return self.token

    @invite_token.setter
    def invite_token(self, val: str) -> None:
        self.token = val


class InventoryTemplateModel(Base):
    __tablename__ = "inventory_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(120), unique=True, nullable=False)
    default_category_name = Column(String(100), default="Pantry", nullable=False)
    default_unit = Column(String(32), default="kg", nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class UnitModel(Base):
    __tablename__ = "units"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    home_id = Column(UUID(as_uuid=True), ForeignKey("homes.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String(64), nullable=False)
    symbol = Column(String(32), nullable=False)
    measurement_type = Column(String(32), default="COUNT", nullable=False)  # WEIGHT, VOLUME, COUNT, LENGTH, OTHER
    is_active = Column(Boolean, default=True, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    home = relationship("HomeModel", back_populates="units")


class InventoryCategoryModel(Base):
    __tablename__ = "inventory_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    home_id = Column(UUID(as_uuid=True), ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    icon = Column(String(50), nullable=True)
    color = Column(String(20), nullable=True)
    sort_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("home_id", "name", name="uq_inventory_categories_home_name"),
    )

    home = relationship("HomeModel", back_populates="inventory_categories")
    items = relationship("InventoryItemModel", back_populates="category")


class LocationModel(Base):
    __tablename__ = "locations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    home_id = Column(UUID(as_uuid=True), ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("locations.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String(120), nullable=False)
    location_type = Column(String(64), default="ZONE", nullable=False)  # ROOM, ZONE, FURNITURE, CONTAINER, SHELF, HOOK, VEHICLE, OTHER
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)
    sort_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("home_id", "parent_id", "name", name="uq_locations_home_parent_name"),
    )

    home = relationship("HomeModel", back_populates="locations")
    parent = relationship("LocationModel", remote_side=[id], backref="children")
    items = relationship(
        "InventoryItemModel",
        back_populates="location",
        foreign_keys="InventoryItemModel.location_id",
    )


class CustomLocationTypeModel(Base):
    __tablename__ = "custom_location_types"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    home_id = Column(UUID(as_uuid=True), ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    code = Column(String(64), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("home_id", "code", name="uq_custom_location_types_home_code"),
    )

    home = relationship("HomeModel", backref="custom_location_types")


class InventoryItemModel(Base):
    __tablename__ = "inventory_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    home_id = Column(UUID(as_uuid=True), ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True)
    template_id = Column(UUID(as_uuid=True), ForeignKey("inventory_templates.id", ondelete="SET NULL"), nullable=True, index=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("inventory_categories.id", ondelete="SET NULL"), nullable=True, index=True)
    location_id = Column(UUID(as_uuid=True), ForeignKey("locations.id", ondelete="SET NULL"), nullable=True, index=True)
    item_type = Column(String(32), default="CONSUMABLE", nullable=False)  # CONSUMABLE, ASSET
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    quantity = Column(Numeric(10, 3), default=Decimal("1.000"), nullable=False)
    unit = Column(String(32), default="pcs", nullable=False)
    min_threshold = Column(Numeric(10, 3), default=Decimal("1.000"), nullable=False)
    preferred_quantity = Column(Numeric(10, 3), nullable=True)
    max_quantity = Column(Numeric(10, 3), nullable=True)
    location_path = Column(Text, nullable=True)
    condition = Column(String(32), nullable=True)  # NEW, EXCELLENT, GOOD, FAIR, POOR, DAMAGED
    asset_status = Column(String(32), default="AVAILABLE", nullable=False)  # AVAILABLE, BORROWED, MISSING, ARCHIVED
    current_holder_name = Column(String(120), nullable=True)
    current_holder_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    last_seen_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    last_seen_location_id = Column(UUID(as_uuid=True), ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)
    expiry_date = Column(Date, nullable=True)
    status = Column(String(32), default="GOOD", nullable=False)  # GOOD, LOW, OUT_OF_STOCK
    expiry_status = Column(String(32), default="NORMAL", nullable=False)  # NORMAL, EXPIRING_SOON, EXPIRED
    notes = Column(Text, nullable=True)

    # Extended Asset Tracking & Home Memory
    brand = Column(String(100), nullable=True)
    model_number = Column(String(100), nullable=True)
    serial_number = Column(String(120), nullable=True, index=True)
    barcode = Column(String(100), nullable=True, index=True)
    qr_code_identifier = Column(String(120), nullable=True, index=True)
    purchase_date = Column(Date, nullable=True)
    purchase_price = Column(Numeric(12, 2), nullable=True)
    purchase_store = Column(String(150), nullable=True)
    warranty_expiry_date = Column(Date, nullable=True)
    warranty_notes = Column(Text, nullable=True)
    photo_url = Column(String(512), nullable=True)
    receipt_url = Column(String(512), nullable=True)
    manual_url = Column(String(512), nullable=True)
    last_serviced_at = Column(Date, nullable=True)
    next_service_due_at = Column(Date, nullable=True)
    service_notes = Column(Text, nullable=True)

    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_inv_items_home_status", "home_id", "status"),
        Index("idx_inv_items_home_type", "home_id", "item_type"),
        Index("idx_inv_items_home_search", "home_id", "name"),
        Index("idx_inv_items_barcode", "home_id", "barcode"),
        Index("idx_inv_items_serial", "home_id", "serial_number"),
    )

    home = relationship("HomeModel", back_populates="inventory_items")
    category = relationship("InventoryCategoryModel", back_populates="items")
    location = relationship(
        "LocationModel",
        back_populates="items",
        foreign_keys=[location_id],
    )
    stock_movements = relationship("StockMovementModel", back_populates="item", cascade="all, delete-orphan")
    location_movements = relationship("LocationMovementModel", back_populates="item", cascade="all, delete-orphan")
    loans = relationship("AssetLoanModel", back_populates="item", cascade="all, delete-orphan")

    def __init__(self, **kwargs):
        if "category" in kwargs and isinstance(kwargs["category"], str):
            kwargs.pop("category")
        if "location" in kwargs and isinstance(kwargs["location"], str):
            kwargs.pop("location")
        if "status" in kwargs:
            kwargs.pop("status")
        super().__init__(**kwargs)


class StockMovementModel(Base):
    __tablename__ = "stock_movements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    home_id = Column(UUID(as_uuid=True), ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = Column(UUID(as_uuid=True), ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False, index=True)
    movement_type = Column(String(32), nullable=False)  # ADD, CONSUME, ADJUST, PURCHASE, WASTE, RETURN
    quantity_delta = Column(Numeric(10, 3), nullable=False)
    previous_quantity = Column(Numeric(10, 3), nullable=False)
    resulting_quantity = Column(Numeric(10, 3), nullable=False)
    reason = Column(Text, nullable=True)
    performed_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        Index("idx_stock_movements_item_time", "item_id", "created_at"),
    )

    home = relationship("HomeModel", back_populates="stock_movements")
    item = relationship("InventoryItemModel", back_populates="stock_movements")


class LocationMovementModel(Base):
    __tablename__ = "location_movements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    home_id = Column(UUID(as_uuid=True), ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = Column(UUID(as_uuid=True), ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False, index=True)
    from_location_id = Column(UUID(as_uuid=True), ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)
    to_location_id = Column(UUID(as_uuid=True), ForeignKey("locations.id", ondelete="RESTRICT"), nullable=False)
    from_location_path = Column(Text, nullable=True)
    to_location_path = Column(Text, nullable=False)
    reason = Column(Text, nullable=True)
    moved_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    moved_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        Index("idx_location_movements_item_time", "item_id", "moved_at"),
    )

    home = relationship("HomeModel", back_populates="location_movements")
    item = relationship("InventoryItemModel", back_populates="location_movements")


class AssetLoanModel(Base):
    __tablename__ = "asset_loans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    home_id = Column(UUID(as_uuid=True), ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = Column(UUID(as_uuid=True), ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False, index=True)
    borrower_type = Column(String(32), default="MEMBER", nullable=False)  # MEMBER, EXTERNAL_PERSON, CONNECTED_HOME
    borrower_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    borrower_name = Column(String(120), nullable=False)
    borrower_contact = Column(String(100), nullable=True)
    loan_status = Column(String(32), default="ACTIVE", nullable=False)  # ACTIVE, RETURNED, OVERDUE, LOST
    borrowed_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    expected_return_at = Column(DateTime(timezone=True), nullable=True)
    returned_at = Column(DateTime(timezone=True), nullable=True)
    return_location_id = Column(UUID(as_uuid=True), ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)
    return_location_path = Column(Text, nullable=True)
    issued_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    received_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        Index("idx_asset_loans_item_time", "item_id", "borrowed_at"),
        Index("idx_asset_loans_home_status", "home_id", "loan_status"),
    )

    home = relationship("HomeModel", back_populates="asset_loans")
    item = relationship("InventoryItemModel", back_populates="loans")


class TaskCategoryModel(Base):
    __tablename__ = "task_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    home_id = Column(UUID(as_uuid=True), ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    icon = Column(String(50), nullable=True)
    color = Column(String(20), nullable=True)
    sort_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        Index("uq_task_categories_home_name", "home_id", "name", unique=True),
    )

    home = relationship("HomeModel", back_populates="task_categories")
    tasks = relationship("TaskModel", back_populates="category")


class TaskTemplateModel(Base):
    __tablename__ = "task_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(150), nullable=False, unique=True, index=True)
    default_category_name = Column(String(100), default="Maintenance", nullable=False)
    default_priority = Column(String(16), default="NORMAL", nullable=False)
    default_recurrence_type = Column(String(32), default="NONE", nullable=False)
    default_interval_days = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class TaskModel(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    home_id = Column(UUID(as_uuid=True), ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True)
    template_id = Column(UUID(as_uuid=True), ForeignKey("task_templates.id", ondelete="SET NULL"), nullable=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("task_categories.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(String(16), default="NORMAL", nullable=False)  # LOW, NORMAL, HIGH, URGENT
    status = Column(String(32), default="TODO", nullable=False)  # TODO, IN_PROGRESS, COMPLETED, CANCELLED
    due_date = Column(DateTime(timezone=True), nullable=True)
    recurrence_type = Column(String(32), default="NONE", nullable=False)  # NONE, DAILY, WEEKLY, MONTHLY, YEARLY, CUSTOM_DAYS
    recurrence_interval_days = Column(Integer, nullable=True)
    recurrence_strategy = Column(String(32), default="SCHEDULED_DATE", nullable=False)  # SCHEDULED_DATE, COMPLETION_DATE
    parent_recurring_task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    bill_id = Column(UUID(as_uuid=True), ForeignKey("bills.id", ondelete="SET NULL"), nullable=True, index=True)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    completed_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_tasks_home_status", "home_id", "status"),
        Index("idx_tasks_home_due", "home_id", "due_date"),
        Index("idx_tasks_home_status_due", "home_id", "status", "due_date"),
        Index("idx_tasks_home_search", "home_id", "title"),
        Index("idx_tasks_home_assigned", "home_id", "assigned_to", "status"),
        Index("idx_tasks_home_bill", "home_id", "bill_id"),
    )

    home = relationship("HomeModel", back_populates="tasks")
    category = relationship("TaskCategoryModel", back_populates="tasks")
    template = relationship("TaskTemplateModel")
    bill = relationship("BillModel", foreign_keys=[bill_id], back_populates="tasks")

    def __init__(self, **kwargs):
        if "category" in kwargs and isinstance(kwargs["category"], str):
            kwargs.pop("category")
        if "template" in kwargs and isinstance(kwargs["template"], str):
            kwargs.pop("template")
        if "recurrence_rule" in kwargs and "recurrence_type" not in kwargs:
            kwargs["recurrence_type"] = kwargs.pop("recurrence_rule")
        super().__init__(**kwargs)

    @property
    def recurrence_rule(self) -> str:
        return self.recurrence_type

    @recurrence_rule.setter
    def recurrence_rule(self, val: str) -> None:
        self.recurrence_type = val


class BillCategoryModel(Base):
    __tablename__ = "bill_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    home_id = Column(UUID(as_uuid=True), ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    icon = Column(String(50), nullable=True)
    color = Column(String(20), nullable=True)
    sort_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("home_id", "name", name="uq_bill_categories_home_name"),
        Index("idx_bill_categories_home_sort", "home_id", "sort_order"),
    )

    home = relationship("HomeModel", back_populates="bill_categories")
    bills = relationship("BillModel", back_populates="category")


class BillTemplateModel(Base):
    __tablename__ = "bill_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(150), nullable=False, unique=True)
    default_category_name = Column(String(100), default="Utilities", nullable=False)
    default_recurrence_type = Column(String(32), default="MONTHLY", nullable=False)
    default_interval_days = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class BillModel(Base):
    __tablename__ = "bills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    home_id = Column(UUID(as_uuid=True), ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True)
    template_id = Column(UUID(as_uuid=True), ForeignKey("bill_templates.id", ondelete="SET NULL"), nullable=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("bill_categories.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(160), nullable=False)
    expected_amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="INR", nullable=False)
    due_date = Column(Date, nullable=False)
    recurrence_type = Column(String(32), default="NONE", nullable=False)  # NONE, MONTHLY, QUARTERLY, HALF_YEARLY, YEARLY, CUSTOM_DAYS
    recurrence_interval_days = Column(Integer, nullable=True)
    recurrence_strategy = Column(String(32), default="SCHEDULED_DATE", nullable=False)  # SCHEDULED_DATE, PAYMENT_DATE
    parent_recurring_bill_id = Column(UUID(as_uuid=True), ForeignKey("bills.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(32), default="UNPAID", nullable=False)  # UNPAID, PARTIALLY_PAID, PAID, CANCELLED
    amount_paid = Column(Numeric(12, 2), default=0.00, nullable=False)
    responsible_member_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Legacy column compatibility mappings
    category_legacy = Column("category", String(64), nullable=True, default="General")
    amount_legacy = Column("amount", Numeric(12, 2), nullable=True)
    recurrence_interval_legacy = Column("recurrence_interval", String(32), nullable=True)

    __table_args__ = (
        Index("idx_bills_home_status", "home_id", "status"),
        Index("idx_bills_home_due", "home_id", "due_date"),
        Index("idx_bills_home_status_due", "home_id", "status", "due_date"),
        Index("idx_bills_home_search", "home_id", "title"),
        Index("idx_bills_home_responsible", "home_id", "responsible_member_id", "status"),
    )

    home = relationship("HomeModel", back_populates="bills")
    category = relationship("BillCategoryModel", back_populates="bills")
    template = relationship("BillTemplateModel")
    reminders = relationship("BillReminderModel", back_populates="bill", cascade="all, delete-orphan")
    payments = relationship("BillPaymentModel", back_populates="bill", cascade="all, delete-orphan")
    tasks = relationship("TaskModel", foreign_keys="TaskModel.bill_id", back_populates="bill")

    def __init__(self, **kwargs):
        if "amount" in kwargs and "expected_amount" not in kwargs:
            kwargs["expected_amount"] = kwargs["amount"]
        if "expected_amount" in kwargs and "amount_legacy" not in kwargs:
            kwargs["amount_legacy"] = kwargs["expected_amount"]
        if "recurrence_interval" in kwargs and "recurrence_type" not in kwargs:
            kwargs["recurrence_type"] = kwargs["recurrence_interval"]
        if "recurrence_type" in kwargs and "recurrence_interval_legacy" not in kwargs:
            kwargs["recurrence_interval_legacy"] = kwargs["recurrence_type"]
        if "category_legacy" not in kwargs:
            kwargs["category_legacy"] = "General"
        super().__init__(**kwargs)

    @property
    def amount(self):
        return self.expected_amount

    @amount.setter
    def amount(self, val):
        self.expected_amount = val

    @property
    def recurrence_interval(self):
        return self.recurrence_type

    @recurrence_interval.setter
    def recurrence_interval(self, val):
        self.recurrence_type = val


class BillReminderModel(Base):
    __tablename__ = "bill_reminders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bill_id = Column(UUID(as_uuid=True), ForeignKey("bills.id", ondelete="CASCADE"), nullable=False, index=True)
    reminder_date = Column(Date, nullable=False)
    is_sent = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    bill = relationship("BillModel", back_populates="reminders")


class BillPaymentModel(Base):
    __tablename__ = "bill_payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    home_id = Column(UUID(as_uuid=True), ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True)
    bill_id = Column(UUID(as_uuid=True), ForeignKey("bills.id", ondelete="CASCADE"), nullable=False, index=True)
    amount_paid = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="INR", nullable=False)
    paid_date = Column(Date, nullable=False)
    paid_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    payment_method = Column(String(32), default="UPI", nullable=False)  # CASH, BANK_TRANSFER, UPI, CARD, ONLINE, OTHER
    receipt_url = Column(String(512), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    home = relationship("HomeModel", back_populates="bill_payments")
    bill = relationship("BillModel", back_populates="payments")
    payer = relationship("UserModel")

    bill = relationship("BillModel", back_populates="payments")


class ShoppingListModel(Base):
    __tablename__ = "shopping_lists"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    home_id = Column(UUID(as_uuid=True), ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    home = relationship("HomeModel", back_populates="shopping_lists")
    items = relationship("ShoppingListItemModel", back_populates="shopping_list", cascade="all, delete-orphan")


class ShoppingListItemModel(Base):
    __tablename__ = "shopping_list_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    home_id = Column(UUID(as_uuid=True), ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True)
    list_id = Column(UUID(as_uuid=True), ForeignKey("shopping_lists.id", ondelete="CASCADE"), nullable=False, index=True)
    inventory_item_id = Column(UUID(as_uuid=True), ForeignKey("inventory_items.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(120), nullable=False)
    quantity = Column(Numeric(10, 2), default=1.0, nullable=False)
    unit = Column(String(32), default="pcs", nullable=False)
    priority = Column(String(16), default="MEDIUM", nullable=False)
    is_checked = Column(Boolean, default=False, nullable=False)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    checked_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    checked_at = Column(DateTime(timezone=True), nullable=True)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        Index("idx_shopping_items_list_checked", "list_id", "is_checked"),
        Index("idx_shopping_items_search", "home_id", "name"),
    )

    shopping_list = relationship("ShoppingListModel", back_populates="items")


class PurchaseItemModel(Base):
    __tablename__ = "purchase_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    home_id = Column(UUID(as_uuid=True), ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True)
    inventory_item_id = Column(UUID(as_uuid=True), ForeignKey("inventory_items.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(150), nullable=False)
    quantity = Column(Numeric(10, 3), default=Decimal("1.000"), nullable=False)
    unit = Column(String(32), default="pcs", nullable=False)
    notes = Column(Text, nullable=True)
    status = Column(String(32), default="PENDING", nullable=False)  # PENDING, PURCHASED, CANCELLED
    added_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    purchased_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    purchased_at = Column(DateTime(timezone=True), nullable=True)
    restocked_to_inventory = Column(Boolean, default=False, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_purchase_items_home_status", "home_id", "status"),
        Index("idx_purchase_items_search", "home_id", "name"),
    )

    home = relationship("HomeModel", back_populates="purchase_items")
    inventory_item = relationship("InventoryItemModel")


class PurchaseHistoryModel(Base):
    __tablename__ = "purchase_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    home_id = Column(UUID(as_uuid=True), ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True)
    purchase_item_id = Column(UUID(as_uuid=True), ForeignKey("purchase_items.id", ondelete="SET NULL"), nullable=True)
    inventory_item_id = Column(UUID(as_uuid=True), ForeignKey("inventory_items.id", ondelete="SET NULL"), nullable=True)
    stock_movement_id = Column(UUID(as_uuid=True), ForeignKey("stock_movements.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(150), nullable=False)
    quantity = Column(Numeric(10, 3), nullable=False)
    unit = Column(String(32), default="pcs", nullable=False)
    purchased_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    purchased_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    restocked_to_inventory = Column(Boolean, default=False, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        Index("idx_purchase_history_home_time", "home_id", "purchased_at"),
    )

    home = relationship("HomeModel", back_populates="purchase_history")
    inventory_item = relationship("InventoryItemModel")


class EventCategoryModel(Base):
    __tablename__ = "event_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    home_id = Column(UUID(as_uuid=True), ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    icon = Column(String(50), nullable=True)
    color = Column(String(20), nullable=True)
    sort_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("home_id", "name", name="uq_event_categories_home_name"),
    )

    home = relationship("HomeModel", back_populates="event_categories")
    events = relationship("EventModel", back_populates="category")


class EventModel(Base):
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    home_id = Column(UUID(as_uuid=True), ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("event_categories.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    is_all_day = Column(Boolean, default=False, nullable=False)
    recurrence_type = Column(String(32), default="NONE", nullable=False)  # NONE, DAILY, WEEKLY, MONTHLY, YEARLY, CUSTOM_DAYS
    recurrence_interval_days = Column(Integer, nullable=True)
    parent_recurring_event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(String(32), default="CONFIRMED", nullable=False)  # CONFIRMED, TENTATIVE, CANCELLED
    reminder_minutes_before = Column(Integer, default=30, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_events_home_time", "home_id", "start_time", "end_time"),
        Index("idx_events_home_search", "home_id", "title"),
        Index("idx_events_home_parent", "home_id", "parent_recurring_event_id"),
    )

    home = relationship("HomeModel", back_populates="events")
    category = relationship("EventCategoryModel", back_populates="events")
    creator = relationship("UserModel", foreign_keys=[created_by])
    participants = relationship("EventParticipantModel", back_populates="event", cascade="all, delete-orphan")


class EventParticipantModel(Base):
    __tablename__ = "event_participants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20), default="INVITED", nullable=False)  # INVITED, ACCEPTED, DECLINED
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("event_id", "user_id", name="uq_event_participants_event_user"),
        Index("idx_event_participants_user", "user_id", "event_id"),
    )

    event = relationship("EventModel", back_populates="participants")
    user = relationship("UserModel")


class NotificationModel(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    home_id = Column(UUID(as_uuid=True), ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(160), nullable=False)
    body = Column(Text, nullable=False)
    type = Column(String(64), nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    read_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        Index("idx_notifications_user_read", "user_id", "is_read", "created_at"),
    )

    user = relationship("UserModel", back_populates="notifications")

    def __init__(self, **kwargs):
        if "notification_type" in kwargs and "type" not in kwargs:
            kwargs["type"] = kwargs.pop("notification_type")
        super().__init__(**kwargs)

    @property
    def notification_type(self) -> str:
        return self.type

    @notification_type.setter
    def notification_type(self, val: str) -> None:
        self.type = val


class UserNotificationPreferencesModel(Base):
    __tablename__ = "user_notification_preferences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    in_app_enabled = Column(Boolean, default=True, nullable=False)
    push_enabled = Column(Boolean, default=True, nullable=False)
    email_enabled = Column(Boolean, default=True, nullable=False)
    sms_enabled = Column(Boolean, default=False, nullable=False)
    whatsapp_enabled = Column(Boolean, default=False, nullable=False)

    task_assigned_enabled = Column(Boolean, default=True, nullable=False)
    bill_reminder_enabled = Column(Boolean, default=True, nullable=False)
    low_stock_enabled = Column(Boolean, default=True, nullable=False)
    event_reminder_enabled = Column(Boolean, default=True, nullable=False)
    home_invitation_enabled = Column(Boolean, default=True, nullable=False)
    system_enabled = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


# ==============================================================================
# DYNAMIC SUBSCRIPTION & PRICING MANAGEMENT DOMAIN ENTITIES
# ==============================================================================

class SubscriptionPlanModel(Base):
    __tablename__ = "subscription_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(120), nullable=False)
    code = Column(String(64), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    plan_type = Column(String(32), default="HOME", nullable=False)  # HOME, INDIVIDUAL, ENTERPRISE
    status = Column(String(32), default="ACTIVE", nullable=False)    # ACTIVE, INACTIVE, ARCHIVED, DRAFT
    included_members = Column(Integer, default=1, nullable=False)
    maximum_members = Column(Integer, default=10, nullable=True)
    additional_member_allowed = Column(Boolean, default=True, nullable=False)
    
    # Configurable Introductory Offer
    introductory_enabled = Column(Boolean, default=True, nullable=False)
    introductory_duration_days = Column(Integer, default=365, nullable=False)
    introductory_price = Column(Numeric(10, 2), default=0.00, nullable=False)
    
    effective_from = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    effective_until = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    prices = relationship("SubscriptionPriceModel", back_populates="plan", cascade="all, delete-orphan")
    plan_features = relationship("SubscriptionPlanFeatureModel", back_populates="plan", cascade="all, delete-orphan")
    subscriptions = relationship("SubscriptionModel", back_populates="plan")
    promotions = relationship("PromotionModel", back_populates="applicable_plan")


class SubscriptionPriceModel(Base):
    __tablename__ = "subscription_prices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("subscription_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    country = Column(String(8), default="GLOBAL", nullable=False, index=True)  # e.g. US, IN, AE, GB, GLOBAL
    region = Column(String(32), default="GLOBAL", nullable=False)             # NORTH_AMERICA, SOUTH_ASIA, etc.
    currency = Column(String(3), default="USD", nullable=False)               # USD, INR, AED, GBP, EUR
    billing_period = Column(String(32), default="ANNUAL", nullable=False)     # MONTHLY, QUARTERLY, HALF_YEARLY, ANNUAL, CUSTOM
    
    # Standard / Published List Prices
    list_price = Column(Numeric(10, 2), default=0.00, nullable=False)                   # Base plan list price
    additional_member_list_price = Column(Numeric(10, 2), default=20.00, nullable=False) # Standard seat list price ($20/yr, ₹1799/yr, AED 99/yr)
    
    # Backward compatibility aliases
    base_price = Column(Numeric(10, 2), default=0.00, nullable=False)
    additional_member_price = Column(Numeric(10, 2), default=10.00, nullable=False)
    
    version = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    effective_from = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    effective_until = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    __table_args__ = (
        UniqueConstraint("plan_id", "country", "billing_period", "version", name="uq_sub_price_version"),
        Index("idx_sub_prices_lookup", "plan_id", "country", "currency", "is_active"),
    )

    plan = relationship("SubscriptionPlanModel", back_populates="prices")


class CampaignModel(Base):
    __tablename__ = "campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(120), nullable=False)
    code = Column(String(64), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    status = Column(String(32), default="ACTIVE", nullable=False)  # ACTIVE, INACTIVE, SCHEDULED, EXPIRED
    start_date = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=True)
    budget_limit = Column(Numeric(12, 2), nullable=True)
    maximum_redemptions = Column(Integer, nullable=True)
    redemptions_count = Column(Integer, default=0, nullable=False)
    country = Column(String(8), nullable=True)
    state = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    coupons = relationship("CouponModel", back_populates="campaign", cascade="all, delete-orphan")


class CouponModel(Base):
    __tablename__ = "coupons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(120), nullable=False)
    code = Column(String(64), unique=True, nullable=False, index=True)  # e.g. WELCOME6, EARLYUSER, SAVE50, VIPFREE
    description = Column(Text, nullable=True)
    coupon_type = Column(String(32), default="PERCENTAGE_DISCOUNT", nullable=False)  # PERCENTAGE_DISCOUNT, FIXED_DISCOUNT, FREE_PERIOD
    discount_value = Column(Numeric(10, 2), default=0.00, nullable=False)
    free_period_value = Column(Integer, default=0, nullable=False)
    free_period_unit = Column(String(16), default="MONTHS", nullable=False)  # DAYS, MONTHS, YEARS
    eligibility_type = Column(String(32), default="ANY_USER", nullable=False)  # ANY_USER, NEW_USER, EXISTING_USER, NEW_HOME, EXISTING_HOME, INVITED_USER, SPECIFIC_USER, SPECIFIC_HOME
    target_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    target_home_id = Column(UUID(as_uuid=True), ForeignKey("homes.id", ondelete="SET NULL"), nullable=True, index=True)
    country = Column(String(8), nullable=True)
    state = Column(String(64), nullable=True)
    district = Column(String(64), nullable=True)
    postal_code = Column(String(32), nullable=True)
    currency = Column(String(3), nullable=True)
    applicable_plan_id = Column(UUID(as_uuid=True), ForeignKey("subscription_plans.id", ondelete="SET NULL"), nullable=True)
    start_date = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=True)
    maximum_total_redemptions = Column(Integer, nullable=True)
    redemptions_count = Column(Integer, default=0, nullable=False)
    maximum_redemptions_per_user = Column(Integer, default=1, nullable=False)
    maximum_redemptions_per_home = Column(Integer, default=1, nullable=False)
    allow_stacking = Column(Boolean, default=False, nullable=False)
    status = Column(String(32), default="ACTIVE", nullable=False)  # ACTIVE, INACTIVE, EXPIRED, SCHEDULED
    notes = Column(Text, nullable=True)
    internal_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    campaign = relationship("CampaignModel", back_populates="coupons")
    applicable_plan = relationship("SubscriptionPlanModel")
    target_user = relationship("UserModel", foreign_keys=[target_user_id])
    target_home = relationship("HomeModel", foreign_keys=[target_home_id])
    redemptions = relationship("CouponRedemptionModel", back_populates="coupon", cascade="all, delete-orphan")


class CouponRedemptionModel(Base):
    __tablename__ = "coupon_redemptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    coupon_id = Column(UUID(as_uuid=True), ForeignKey("coupons.id", ondelete="CASCADE"), nullable=False, index=True)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    home_id = Column(UUID(as_uuid=True), ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True)
    discount_amount_applied = Column(Numeric(10, 2), default=0.00, nullable=False)
    free_days_granted = Column(Integer, default=0, nullable=False)
    redeemed_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    coupon = relationship("CouponModel", back_populates="redemptions")
    user = relationship("UserModel")
    home = relationship("HomeModel")


class SubscriptionGrantModel(Base):
    __tablename__ = "subscription_grants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    home_id = Column(UUID(as_uuid=True), ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("subscription_plans.id", ondelete="RESTRICT"), nullable=False)
    grant_type = Column(String(32), default="FREE_PERIOD", nullable=False)  # FREE_PERIOD, PERCENTAGE_DISCOUNT, FIXED_DISCOUNT, EXTENDED_TRIAL
    duration_value = Column(Integer, default=0, nullable=False)
    duration_unit = Column(String(16), default="MONTHS", nullable=False)  # DAYS, MONTHS, YEARS
    discount_value = Column(Numeric(10, 2), default=0.00, nullable=False)
    start_date = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    expiry_date = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(32), default="ACTIVE", nullable=False)  # ACTIVE, EXPIRED, REVOKED
    reason = Column(Text, nullable=False)
    granted_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    home = relationship("HomeModel")
    plan = relationship("SubscriptionPlanModel")
    granter = relationship("UserModel", foreign_keys=[granted_by])


class PromotionModel(Base):
    __tablename__ = "promotions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(120), nullable=False)
    code = Column(String(64), unique=True, nullable=False, index=True)  # e.g. LAUNCH50, FOUNDING_HOME, EARLY_ADOPTER
    description = Column(Text, nullable=True)
    discount_type = Column(String(32), default="PERCENTAGE", nullable=False)  # PERCENTAGE, FIXED_AMOUNT
    discount_value = Column(Numeric(10, 2), default=50.00, nullable=False)    # 50.00 for 50%, or fixed amount
    start_date = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(32), default="ACTIVE", nullable=False)             # ACTIVE, INACTIVE, EXPIRED, SCHEDULED
    currency = Column(String(3), nullable=True)                               # Specific currency or NULL for all
    country = Column(String(8), nullable=True)                                # Specific country or NULL for all
    region = Column(String(32), nullable=True)
    applicable_plan_id = Column(UUID(as_uuid=True), ForeignKey("subscription_plans.id", ondelete="SET NULL"), nullable=True)
    new_users_only = Column(Boolean, default=False, nullable=False)
    existing_users_allowed = Column(Boolean, default=True, nullable=False)
    maximum_redemptions = Column(Integer, nullable=True)
    redemptions_count = Column(Integer, default=0, nullable=False)
    maximum_redemptions_per_user = Column(Integer, default=1, nullable=False)
    minimum_purchase = Column(Numeric(10, 2), default=0.00, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    applicable_plan = relationship("SubscriptionPlanModel", back_populates="promotions")
    redemptions = relationship("PromotionRedemptionModel", back_populates="promotion", cascade="all, delete-orphan")


class PromotionRedemptionModel(Base):
    __tablename__ = "promotion_redemptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    promotion_id = Column(UUID(as_uuid=True), ForeignKey("promotions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    home_id = Column(UUID(as_uuid=True), ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True)
    discount_amount_applied = Column(Numeric(10, 2), default=0.00, nullable=False)
    redeemed_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    promotion = relationship("PromotionModel", back_populates="redemptions")
    user = relationship("UserModel")
    home = relationship("HomeModel")


class SubscriptionFeatureModel(Base):
    __tablename__ = "subscription_features"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    plan_features = relationship("SubscriptionPlanFeatureModel", back_populates="feature", cascade="all, delete-orphan")


class SubscriptionPlanFeatureModel(Base):
    __tablename__ = "subscription_plan_features"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("subscription_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    feature_id = Column(UUID(as_uuid=True), ForeignKey("subscription_features.id", ondelete="CASCADE"), nullable=False, index=True)
    is_enabled = Column(Boolean, default=True, nullable=False)
    entitlement_limit = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("plan_id", "feature_id", name="uq_plan_feature_mapping"),
    )

    plan = relationship("SubscriptionPlanModel", back_populates="plan_features")
    feature = relationship("SubscriptionFeatureModel", back_populates="plan_features")


class SubscriptionModel(Base):
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    home_id = Column(UUID(as_uuid=True), ForeignKey("homes.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("subscription_plans.id", ondelete="RESTRICT"), nullable=False)
    price_id = Column(UUID(as_uuid=True), ForeignKey("subscription_prices.id", ondelete="RESTRICT"), nullable=True)
    active_coupon_id = Column(UUID(as_uuid=True), ForeignKey("coupons.id", ondelete="SET NULL"), nullable=True)
    active_grant_id = Column(UUID(as_uuid=True), ForeignKey("subscription_grants.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(32), default="TRIALING", nullable=False)  # TRIALING, ACTIVE, PAST_DUE, CANCELED, EXPIRED, RENEWAL_REQUIRED
    introductory_period_starts_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    introductory_period_ends_at = Column(DateTime(timezone=True), nullable=False)
    current_period_starts_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    current_period_ends_at = Column(DateTime(timezone=True), nullable=False)
    free_period_ends_at = Column(DateTime(timezone=True), nullable=True)
    is_free_period_active = Column(Boolean, default=False, nullable=False)
    paid_member_seats = Column(Integer, default=0, nullable=False)
    
    # Comprehensive Immutable Historical Pricing Snapshot
    list_price_snapshot = Column(Numeric(10, 2), default=0.00, nullable=False)
    additional_member_list_price_snapshot = Column(Numeric(10, 2), default=20.00, nullable=False)
    discount_type_snapshot = Column(String(32), default="PERCENTAGE", nullable=False)
    discount_value_snapshot = Column(Numeric(10, 2), default=50.00, nullable=False)
    discount_amount_snapshot = Column(Numeric(10, 2), default=10.00, nullable=False)
    effective_price_snapshot = Column(Numeric(10, 2), default=10.00, nullable=False)
    promotion_code_snapshot = Column(String(64), nullable=True)
    currency_snapshot = Column(String(3), default="USD", nullable=False)
    pricing_date_snapshot = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    renewal_policy = Column(String(32), default="KEEP_ORIGINAL_PRICE", nullable=False)
    
    # Backward compatibility locked columns
    currency = Column(String(3), default="USD", nullable=False)
    base_price_locked = Column(Numeric(10, 2), default=0.00, nullable=False)
    additional_member_price_locked = Column(Numeric(10, 2), default=10.00, nullable=False)
    
    cancel_at_period_end = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        Index("idx_subscriptions_home_status", "home_id", "status"),
    )

    home = relationship("HomeModel", back_populates="subscription")
    plan = relationship("SubscriptionPlanModel", back_populates="subscriptions")
    price = relationship("SubscriptionPriceModel")
    active_coupon = relationship("CouponModel")
    active_grant = relationship("SubscriptionGrantModel")


class SubscriptionAuditLogModel(Base):
    __tablename__ = "subscription_audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type = Column(String(64), nullable=False, index=True)  # PLAN, PRICE, PROMOTION, FEATURE, SUBSCRIPTION
    entity_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    action = Column(String(32), nullable=False)                  # CREATE, UPDATE, ACTIVATE, DEACTIVATE, SCHEDULE_PRICE
    performed_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    old_values = Column(Text, nullable=True)                     # JSON string
    new_values = Column(Text, nullable=True)                     # JSON string
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    __table_args__ = (
        Index("idx_sub_audit_entity", "entity_type", "entity_id", "created_at"),
    )
