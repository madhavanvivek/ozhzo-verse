import uuid
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint
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
    free_home_consumed = Column(Boolean, default=False, nullable=False, index=True)
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
    public_home_id = Column(String(16), unique=True, index=True, nullable=True)
    home_qr_token = Column(String(128), unique=True, index=True, nullable=True)
    home_qr_status = Column(String(32), default="ACTIVE", nullable=False)  # ACTIVE, REVOKED, DISABLED
    home_qr_version = Column(Integer, default=1, nullable=False)
    home_qr_created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    home_qr_revoked_at = Column(DateTime(timezone=True), nullable=True)
    country = Column(String(8), nullable=True)
    state_province = Column(String(64), nullable=True)
    district_city = Column(String(64), nullable=True)
    postal_code = Column(String(32), nullable=True)
    currency = Column(String(3), default="USD", nullable=False)
    timezone = Column(String(64), default="UTC", nullable=False)
    address = Column(Text, nullable=True)
    avatar_url = Column(String(512), nullable=True)
    join_policy = Column(String(32), default="REQUEST_TO_JOIN", nullable=False)  # REQUEST_TO_JOIN, INVITE_ONLY, PUBLIC_JOIN
    status = Column(String(32), default="ACTIVE", nullable=False)  # ACTIVE, SUSPENDED
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    members = relationship("HomeMemberModel", back_populates="home", cascade="all, delete-orphan")
    invitations = relationship("InvitationModel", back_populates="home", cascade="all, delete-orphan")
    join_requests = relationship("HomeJoinRequestModel", back_populates="home", cascade="all, delete-orphan")
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
    automations = relationship("AutomationModel", back_populates="home", cascade="all, delete-orphan")
    subscription = relationship("SubscriptionModel", back_populates="home", uselist=False, cascade="all, delete-orphan")
    access_entitlements = relationship("HomeAccessEntitlementModel", back_populates="home", cascade="all, delete-orphan")


class HomeJoinRequestModel(Base):
    __tablename__ = "home_join_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    home_id = Column(UUID(as_uuid=True), ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(32), default="PENDING", nullable=False)  # PENDING, APPROVED, REJECTED, CANCELLED
    message = Column(Text, nullable=True)
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        Index("idx_join_requests_home_status", "home_id", "status"),
        Index("idx_join_requests_user_status", "user_id", "status"),
    )

    home = relationship("HomeModel", back_populates="join_requests")
    user = relationship("UserModel", foreign_keys=[user_id])
    reviewer = relationship("UserModel", foreign_keys=[reviewed_by])


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
    home_id = Column(UUID(as_uuid=True), ForeignKey("homes.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(160), nullable=False)
    body = Column(Text, nullable=False)
    type = Column(String(64), nullable=False)
    priority = Column(String(32), default="NORMAL", nullable=False)  # CRITICAL, HIGH, NORMAL, LOW
    requires_action = Column(Boolean, default=False, nullable=False)
    action_status = Column(String(32), default="OPEN", nullable=False)  # OPEN, ACKNOWLEDGED, RESOLVED, DISMISSED
    action_type = Column(String(64), nullable=True)                  # RENEW, JOIN_HOME, RETRY_PAYMENT, REVIEW_RESERVATION
    action_url = Column(String(255), nullable=True)
    action_label = Column(String(64), nullable=True)
    dedup_key = Column(String(128), nullable=True, index=True)
    extra_metadata = Column(Text, nullable=True)
    is_read = Column(Boolean, default=False, nullable=False)
    read_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    dismissed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        Index("idx_notifications_user_read", "user_id", "is_read", "created_at"),
        Index("idx_notifications_user_prio_read", "user_id", "priority", "is_read", "created_at"),
        Index("idx_notifications_user_action_status", "user_id", "requires_action", "action_status"),
        Index("idx_notifications_dedup", "dedup_key"),
    )

    user = relationship("UserModel", back_populates="notifications")
    home = relationship("HomeModel")

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
    max_homes = Column(Integer, default=10, nullable=False)
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
    
    # Standard / Published List Prices & Commercial Model
    country_name = Column(String(100), default="", nullable=False)
    country_iso3 = Column(String(4), default="", nullable=False)
    currency_symbol = Column(String(16), default="", nullable=False)
    
    # Regular Commercial Price (Authoritative long-term commercial price)
    regular_price = Column(Numeric(10, 2), default=0.00, nullable=False)
    list_price = Column(Numeric(10, 2), default=0.00, nullable=False)                   # Base plan list price (alias)
    additional_member_list_price = Column(Numeric(10, 2), default=20.00, nullable=False) # Standard seat list price ($20/yr, ₹1799/yr, AED 99/yr)
    
    # Campaign / Offer Price (Active promotional selling price)
    offer_price = Column(Numeric(10, 2), nullable=True)
    campaign_name = Column(String(150), nullable=True)
    campaign_description = Column(Text, nullable=True)
    offer_status = Column(String(32), default="DRAFT", nullable=False)  # DRAFT, SCHEDULED, ACTIVE, EXPIRED, CANCELLED
    offer_start_date = Column(DateTime(timezone=True), nullable=True)
    offer_end_date = Column(DateTime(timezone=True), nullable=True)
    
    # Tax & Policy Configurations
    tax_percentage = Column(Numeric(5, 2), default=0.00, nullable=False)
    allow_coupon_stacking = Column(Boolean, default=False, nullable=False)
    
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
    country = Column(String(255), nullable=True)
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
    country = Column(String(255), nullable=True)
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
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
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
        Index("idx_subscriptions_user_status", "user_id", "status"),
    )

    home = relationship("HomeModel", back_populates="subscription")
    user = relationship("UserModel", foreign_keys=[user_id])
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


class PaymentTransactionModel(Base):
    __tablename__ = "payment_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    home_id = Column(UUID(as_uuid=True), ForeignKey("homes.id", ondelete="SET NULL"), nullable=True, index=True)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True, index=True)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("subscription_plans.id", ondelete="RESTRICT"), nullable=False, index=True)
    price_id = Column(UUID(as_uuid=True), ForeignKey("subscription_prices.id", ondelete="SET NULL"), nullable=True)
    coupon_id = Column(UUID(as_uuid=True), ForeignKey("coupons.id", ondelete="SET NULL"), nullable=True)

    amount = Column(Numeric(10, 2), default=0.00, nullable=False)
    discount_amount = Column(Numeric(10, 2), default=0.00, nullable=False)
    credit_amount = Column(Numeric(10, 2), default=0.00, nullable=False)
    tax_amount = Column(Numeric(10, 2), default=0.00, nullable=False)
    final_amount = Column(Numeric(10, 2), default=0.00, nullable=False)
    currency = Column(String(3), default="USD", nullable=False)

    provider = Column(String(32), default="MOCK_GATEWAY", nullable=False)  # MOCK_GATEWAY, STRIPE, RAZORPAY
    provider_transaction_id = Column(String(128), nullable=True, index=True)
    idempotency_key = Column(String(128), unique=True, nullable=True, index=True)
    status = Column(String(32), default="PENDING", nullable=False)  # CREATED, PENDING, SUCCESS, FAILED, CANCELLED, REFUNDED
    failure_reason = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        Index("idx_pay_trans_user_status", "user_id", "status"),
        Index("idx_pay_trans_created", "created_at"),
    )

    user = relationship("UserModel", foreign_keys=[user_id])
    home = relationship("HomeModel", foreign_keys=[home_id])
    subscription = relationship("SubscriptionModel", foreign_keys=[subscription_id])
    plan = relationship("SubscriptionPlanModel", foreign_keys=[plan_id])
    price = relationship("SubscriptionPriceModel", foreign_keys=[price_id])
    coupon = relationship("CouponModel", foreign_keys=[coupon_id])


# ==============================================================================
# HOME ACCESS ENTITLEMENTS (PER PERSON + PER HOME ACCESS GRANTS & RESERVATIONS)
# ==============================================================================

class HomeAccessEntitlementModel(Base):
    __tablename__ = "home_access_entitlements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    home_id = Column(UUID(as_uuid=True), ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True, index=True)

    # Verified Identity Binding for Reservations
    reserved_identifier_type = Column(String(16), nullable=True)  # PHONE, EMAIL
    reserved_identifier_value = Column(String(255), nullable=True, index=True)  # Normalized phone or lowercase email

    # Commercial Entitlement Classification
    entitlement_type = Column(String(32), default="FIRST_YEAR_FREE", nullable=False)  # FIRST_YEAR_FREE, PAID_SEAT, RESERVATION, DIRECT_USER_SUBSCRIPTION, ADMIN_GRANT
    status = Column(String(32), default="ACTIVE", nullable=False, index=True)  # PENDING, RESERVED, ACTIVE, EXPIRING, EXPIRED, CANCELLED

    starts_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)

    notes = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        Index("idx_entitlement_home_user", "home_id", "user_id", "status"),
        Index("idx_entitlement_reservation", "reserved_identifier_value", "status"),
        Index("idx_entitlement_expiry", "expires_at", "status"),
    )

    home = relationship("HomeModel", back_populates="access_entitlements")
    user = relationship("UserModel", foreign_keys=[user_id])
    subscription = relationship("SubscriptionModel", foreign_keys=[subscription_id])
    creator = relationship("UserModel", foreign_keys=[created_by])


# ==============================================================================
# SUBSCRIPTION CREDIT LEDGER (REUSABLE SUBSCRIPTION VALUE)
# ==============================================================================

class SubscriptionCreditModel(Base):
    __tablename__ = "subscription_credits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    home_id = Column(UUID(as_uuid=True), ForeignKey("homes.id", ondelete="SET NULL"), nullable=True, index=True)

    amount = Column(Numeric(10, 2), default=0.00, nullable=False)
    remaining_amount = Column(Numeric(10, 2), default=0.00, nullable=False)
    currency = Column(String(3), default="USD", nullable=False)

    credit_type = Column(String(32), default="ADMIN_GRANT", nullable=False)  # RESERVATION_RELEASE, ADMIN_GRANT, PAYMENT_ADJUSTMENT, COMPENSATION
    status = Column(String(32), default="AVAILABLE", nullable=False, index=True)  # AVAILABLE, PARTIALLY_USED, REDEEMED, EXPIRED, CANCELLED

    source_type = Column(String(64), nullable=True)  # PAYMENT_TRANSACTION, RESERVATION_RELEASE, ADMIN_MANUAL, PROMOTION
    source_id = Column(UUID(as_uuid=True), nullable=True)
    reference = Column(String(128), nullable=True)
    description = Column(Text, nullable=True)

    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    redeemed_transaction_id = Column(UUID(as_uuid=True), ForeignKey("payment_transactions.id", ondelete="SET NULL"), nullable=True)

    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        Index("idx_sub_credits_user_status", "user_id", "status"),
        Index("idx_sub_credits_user_curr_status", "user_id", "currency", "status"),
        Index("idx_sub_credits_home_status", "home_id", "status"),
        Index("idx_sub_credits_created", "created_at"),
    )

    user = relationship("UserModel", foreign_keys=[user_id])
    home = relationship("HomeModel", foreign_keys=[home_id])
    creator = relationship("UserModel", foreign_keys=[created_by])
    redeemed_transaction = relationship("PaymentTransactionModel", foreign_keys=[redeemed_transaction_id])


# ==============================================================================
# STAGE 4: ADVANCED HOUSEHOLD AUTOMATION & PREDICTIVE INTELLIGENCE
# ==============================================================================

class AutomationModel(Base):
    __tablename__ = "automations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    home_id = Column(UUID(as_uuid=True), ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, default=True, nullable=False, index=True)

    trigger_type = Column(String(64), nullable=False, index=True)
    # Conditions structure: {"operator": "AND"|"OR", "rules": [{"field": str, "op": str, "value": any}]}
    conditions = Column(JSON, default=dict, nullable=False)
    # Actions structure: [{"action_type": str, "params": dict}]
    actions = Column(JSON, default=list, nullable=False)
    # Schedule config: {"cron": str, "timezone": str, "interval_days": int}
    schedule = Column(JSON, default=dict, nullable=False)
    # Execution policy: {"max_retries": int, "retry_backoff_sec": int}
    execution_policy = Column(JSON, default=dict, nullable=False)

    last_run_at = Column(DateTime(timezone=True), nullable=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True, index=True)
    status = Column(String(32), default="ACTIVE", nullable=False, index=True)  # ACTIVE, PAUSED, DISABLED, ERROR

    failure_count = Column(Integer, default=0, nullable=False)
    consecutive_failures = Column(Integer, default=0, nullable=False)
    version = Column(Integer, default=1, nullable=False)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_automations_home_status", "home_id", "status"),
        Index("idx_automations_home_trigger", "home_id", "trigger_type"),
        Index("idx_automations_schedule_poll", "status", "enabled", "next_run_at"),
    )

    home = relationship("HomeModel", back_populates="automations")
    creator = relationship("UserModel", foreign_keys=[created_by])
    executions = relationship("AutomationExecutionModel", back_populates="automation", cascade="all, delete-orphan")


class AutomationExecutionModel(Base):
    __tablename__ = "automation_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    automation_id = Column(UUID(as_uuid=True), ForeignKey("automations.id", ondelete="CASCADE"), nullable=False, index=True)
    home_id = Column(UUID(as_uuid=True), ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True)

    trigger_event = Column(JSON, default=dict, nullable=False)
    evaluated_conditions = Column(JSON, default=dict, nullable=False)

    actions_attempted = Column(Integer, default=0, nullable=False)
    actions_succeeded = Column(Integer, default=0, nullable=False)
    actions_failed = Column(Integer, default=0, nullable=False)
    duration_ms = Column(Integer, default=0, nullable=False)

    status = Column(String(32), default="SUCCESS", nullable=False, index=True)  # SUCCESS, PARTIAL, FAILED, SKIPPED
    error_details = Column(Text, nullable=True)

    correlation_id = Column(String(64), nullable=True, index=True)
    idempotency_key = Column(String(128), unique=True, index=True, nullable=False)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    __table_args__ = (
        Index("idx_auto_exec_home_created", "home_id", "created_at"),
        Index("idx_auto_exec_auto_created", "automation_id", "created_at"),
    )

    automation = relationship("AutomationModel", back_populates="executions")
    home = relationship("HomeModel", foreign_keys=[home_id])


class HouseholdRecommendationModel(Base):
    __tablename__ = "household_recommendations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    home_id = Column(UUID(as_uuid=True), ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True)

    domain = Column(String(64), nullable=False, index=True)  # TASK, BILL, INVENTORY, SHOPPING, AUTOMATION
    title = Column(String(200), nullable=False)
    reason = Column(Text, nullable=False)
    confidence = Column(Numeric(3, 2), default=Decimal("0.90"), nullable=False)
    source_category = Column(String(64), default="PATTERN_ANALYSIS", nullable=False)

    suggested_action = Column(JSON, nullable=True)
    status = Column(String(32), default="NEW", nullable=False, index=True)  # NEW, VIEWED, ACCEPTED, DISMISSED, EXPIRED

    dedup_hash = Column(String(64), index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)

    __table_args__ = (
        Index("idx_hh_recs_home_status", "home_id", "status"),
        Index("idx_hh_recs_home_domain", "home_id", "domain"),
        Index("idx_hh_recs_dedup", "home_id", "dedup_hash"),
    )

    home = relationship("HomeModel", foreign_keys=[home_id])


class HouseholdMemoryModel(Base):
    __tablename__ = "household_memories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    home_id = Column(UUID(as_uuid=True), ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    category = Column(String(64), nullable=False, index=True)  # PREFERENCE, ROUTINE, HOUSEHOLD_PATTERN, IMPORTANT_FACT, RECURRING_BEHAVIOR, USER_INSTRUCTION, DISMISSED_PREFERENCE, AUTOMATION_PREFERENCE
    content = Column(Text, nullable=False)
    source = Column(String(64), default="SYSTEM_INFERRED", nullable=False)  # USER_PROVIDED, USER_CONFIRMED, SYSTEM_INFERRED, AI_INFERRED
    confidence = Column(Numeric(3, 2), default=Decimal("0.90"), nullable=False)
    status = Column(String(32), default="ACTIVE", nullable=False, index=True)  # ACTIVE, DISMISSED, EXPIRED, ARCHIVED

    context_metadata = Column(JSON, default=dict, nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_hh_mem_home_status", "home_id", "status"),
        Index("idx_hh_mem_home_cat", "home_id", "category"),
        Index("idx_hh_mem_user_home", "user_id", "home_id"),
    )

    home = relationship("HomeModel", foreign_keys=[home_id])
    user = relationship("UserModel", foreign_keys=[user_id])


class UserPersonalizationPreferenceModel(Base):
    __tablename__ = "user_personalization_preferences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    home_id = Column(UUID(as_uuid=True), ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True)

    personalization_enabled = Column(Boolean, default=True, nullable=False)
    ai_memory_enabled = Column(Boolean, default=True, nullable=False)
    reminder_timing_preference = Column(String(64), default="1_DAY_BEFORE", nullable=False)  # 1_DAY_BEFORE, SAME_DAY_MORNING, SAME_DAY_EVENING, 2_DAYS_BEFORE
    recommendation_frequency = Column(String(32), default="BALANCED", nullable=False)  # HIGH, BALANCED, LOW, MUTED
    digest_enabled = Column(Boolean, default=True, nullable=False)
    digest_day_of_week = Column(String(16), default="SUNDAY", nullable=False)

    preferences_json = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "home_id", name="uq_user_home_personalization"),
    )

    user = relationship("UserModel", foreign_keys=[user_id])
    home = relationship("HomeModel", foreign_keys=[home_id])


class AIConversationSessionModel(Base):
    __tablename__ = "ai_conversation_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    home_id = Column(UUID(as_uuid=True), ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    session_token = Column(String(64), unique=True, index=True, nullable=False)
    history_json = Column(JSON, default=list, nullable=False)
    active_plan = Column(JSON, nullable=True)

    last_activity_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    home = relationship("HomeModel", foreign_keys=[home_id])
    user = relationship("UserModel", foreign_keys=[user_id])


class AIAgentAuditModel(Base):
    __tablename__ = "ai_agent_audits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    home_id = Column(UUID(as_uuid=True), ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    event_type = Column(String(64), nullable=False, index=True)  # MEMORY_CREATED, MEMORY_UPDATED, MEMORY_DELETED, TOOL_INVOKED, PLAN_GENERATED, PLAN_CONFIRMED, PLAN_REJECTED, PLAN_EXECUTED, PROPOSAL_CONFIRMED, PROPOSAL_REJECTED, PREFERENCES_UPDATED
    tool_name = Column(String(64), nullable=True)
    tool_params = Column(JSON, nullable=True)
    execution_status = Column(String(32), default="SUCCESS", nullable=False)  # SUCCESS, FAILED, CANCELLED, REJECTED
    details = Column(Text, nullable=True)
    correlation_id = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    home = relationship("HomeModel", foreign_keys=[home_id])
    user = relationship("UserModel", foreign_keys=[user_id])


class AIUsageRecordModel(Base):
    __tablename__ = "ai_usage_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    home_id = Column(UUID(as_uuid=True), ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    provider = Column(String(32), default="mock", nullable=False)
    model_name = Column(String(64), default="ozhzo-neural-v1", nullable=False)
    prompt_tokens = Column(Integer, default=0, nullable=False)
    completion_tokens = Column(Integer, default=0, nullable=False)
    total_tokens = Column(Integer, default=0, nullable=False)
    estimated_cost_usd = Column(Numeric(10, 6), default=Decimal("0.000000"), nullable=False)
    latency_ms = Column(Integer, default=0, nullable=False)
    status = Column(String(32), default="SUCCESS", nullable=False)  # SUCCESS, QUOTA_EXCEEDED, FAILED
    correlation_id = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    __table_args__ = (
        Index("idx_ai_usage_home_time", "home_id", "created_at"),
        Index("idx_ai_usage_user_time", "user_id", "created_at"),
    )

    home = relationship("HomeModel", foreign_keys=[home_id])
    user = relationship("UserModel", foreign_keys=[user_id])


class AIUsageQuotaModel(Base):
    __tablename__ = "ai_usage_quotas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    home_id = Column(UUID(as_uuid=True), ForeignKey("homes.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    daily_request_limit = Column(Integer, default=100, nullable=False)
    daily_token_limit = Column(Integer, default=100000, nullable=False)
    monthly_cost_limit_usd = Column(Numeric(8, 2), default=Decimal("5.00"), nullable=False)

    current_daily_requests = Column(Integer, default=0, nullable=False)
    current_daily_tokens = Column(Integer, default=0, nullable=False)
    current_monthly_cost_usd = Column(Numeric(8, 2), default=Decimal("0.00"), nullable=False)

    last_daily_reset_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    last_monthly_reset_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    home = relationship("HomeModel", foreign_keys=[home_id])


class BackgroundJobModel(Base):
    __tablename__ = "background_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_type = Column(String(64), nullable=False, index=True)  # NOTIFICATION_DISPATCH, RETENTION_PURGE, WEEKLY_DIGEST, WEBHOOK_RETRY, MAINTENANCE
    home_id = Column(UUID(as_uuid=True), ForeignKey("homes.id", ondelete="CASCADE"), nullable=True, index=True)

    payload = Column(JSON, default=dict, nullable=False)
    status = Column(String(32), default="PENDING", nullable=False, index=True)  # PENDING, RUNNING, COMPLETED, FAILED, DEAD_LETTER
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)

    next_run_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    locked_at = Column(DateTime(timezone=True), nullable=True)
    locked_by = Column(String(64), nullable=True)
    last_error = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    idempotency_key = Column(String(128), unique=True, nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        Index("idx_bg_jobs_status_next_run", "status", "next_run_at"),
        Index("idx_bg_jobs_type_status", "job_type", "status"),
    )

    home = relationship("HomeModel", foreign_keys=[home_id])


# ==============================================================================
# SUPER ADMIN OPERATIONAL CONTROL & DYNAMIC CONFIGURATION
# ==============================================================================

class RegionConfigModel(Base):
    __tablename__ = "region_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    country_code = Column(String(8), unique=True, index=True, nullable=False)  # IN, AE, SA, GB, US, GLOBAL
    country_name = Column(String(100), nullable=False)
    region = Column(String(64), nullable=False, default="Global")  # South Asia, Middle East, Europe, North America
    currency = Column(String(8), nullable=False, default="USD")
    default_plan_code = Column(String(64), nullable=False, default="HOME_STANDARD")
    payment_gateway = Column(String(64), nullable=False, default="STRIPE")  # STRIPE, RAZORPAY, MOCK
    tax_percentage = Column(Numeric(5, 2), default=Decimal("0.00"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_default = Column(Boolean, default=False, nullable=False)
    promotional_eligibility_enabled = Column(Boolean, default=True, nullable=False)
    metadata_json = Column(JSON, default=dict, nullable=False)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class FeatureFlagModel(Base):
    __tablename__ = "feature_flags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    is_enabled = Column(Boolean, default=False, nullable=False, index=True)
    target_countries = Column(JSON, default=list, nullable=False)  # e.g. ["IN", "AE"] or [] for all
    target_plans = Column(JSON, default=list, nullable=False)  # e.g. ["HOME_STANDARD"] or [] for all
    rollout_percentage = Column(Integer, default=100, nullable=False)
    rules_json = Column(JSON, default=dict, nullable=False)
    starts_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    creator = relationship("UserModel", foreign_keys=[created_by])


class SystemCommercialRuleModel(Base):
    __tablename__ = "system_commercial_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_key = Column(String(100), unique=True, index=True, nullable=False)
    rule_name = Column(String(150), nullable=False)
    rule_value = Column(JSON, default=dict, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(64), default="SUBSCRIPTION", nullable=False, index=True)  # SUBSCRIPTION, ENTITLEMENT, BILLING
    is_active = Column(Boolean, default=True, nullable=False)

    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    updater = relationship("UserModel", foreign_keys=[updated_by])






