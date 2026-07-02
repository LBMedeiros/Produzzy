from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy import UniqueConstraint, text
from sqlalchemy.orm import relationship

from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        Index(
            "uq_categories_workspace_name_active",
            "workspace_id",
            "name",
            unique=True,
            postgresql_where=text("is_active = true"),
            sqlite_where=text("is_active = 1"),
        ),
        Index("ix_categories_workspace_is_active", "workspace_id", "is_active"),
    )

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(
        Integer,
        ForeignKey("workspaces.id"),
        nullable=False,
        index=True,
    )

    name = Column(String(100), nullable=False, index=True)
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by_user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    workspace = relationship(
        "Workspace",
        back_populates="categories",
    )
    deleted_by_user = relationship(
        "User",
        foreign_keys=[deleted_by_user_id],
    )


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        Index(
            "uq_products_workspace_name_active",
            "workspace_id",
            "name",
            unique=True,
            postgresql_where=text("is_active = true"),
            sqlite_where=text("is_active = 1"),
        ),
        Index("ix_products_workspace_is_active", "workspace_id", "is_active"),
    )

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(
        Integer,
        ForeignKey("workspaces.id"),
        nullable=False,
        index=True,
    )

    name = Column(String(100), nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)

    quantity = Column(Integer, nullable=False, default=0)
    minimum_quantity = Column(Integer, nullable=False, default=0)

    is_active = Column(Boolean, nullable=False, default=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by_user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )
    deleted_by_category_id = Column(
        Integer,
        ForeignKey("categories.id"),
        nullable=True,
        index=True,
    )

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    workspace = relationship(
        "Workspace",
        back_populates="products",
    )
    deleted_by_user = relationship(
        "User",
        back_populates="deleted_products",
        foreign_keys=[deleted_by_user_id],
    )
    deleted_by_category = relationship(
        "Category",
        foreign_keys=[deleted_by_category_id],
    )
    stock_movements = relationship(
        "StockMovement",
        back_populates="product",
        cascade="all, delete-orphan",
    )
    replenishment_requests = relationship(
        "ReplenishmentRequest",
        back_populates="product",
    )


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    stock_movements = relationship(
        "StockMovement",
        back_populates="user",
    )
    audit_logs = relationship(
        "AuditLog",
        back_populates="user",
    )
    deleted_products = relationship(
        "Product",
        back_populates="deleted_by_user",
        foreign_keys="Product.deleted_by_user_id",
    )
    owned_workspaces = relationship(
        "Workspace",
        back_populates="owner",
        foreign_keys="Workspace.owner_id",
    )
    workspace_memberships = relationship(
        "WorkspaceMember",
        back_populates="user",
    )
    created_workspace_invites = relationship(
        "WorkspaceInvite",
        back_populates="created_by_user",
        foreign_keys="WorkspaceInvite.created_by_user_id",
    )
    accepted_workspace_invites = relationship(
        "WorkspaceInvite",
        back_populates="accepted_by_user",
        foreign_keys="WorkspaceInvite.accepted_by_user_id",
    )
    created_replenishment_requests = relationship(
        "ReplenishmentRequest",
        back_populates="created_by_user",
        foreign_keys="ReplenishmentRequest.created_by_user_id",
    )
    assigned_replenishment_requests = relationship(
        "ReplenishmentRequest",
        back_populates="assigned_to_user",
        foreign_keys="ReplenishmentRequest.assigned_to_user_id",
    )
    replenishment_assignments = relationship(
        "ReplenishmentAssignee",
        back_populates="user",
        foreign_keys="ReplenishmentAssignee.user_id",
    )
    created_replenishment_assignments = relationship(
        "ReplenishmentAssignee",
        back_populates="assigned_by_user",
        foreign_keys="ReplenishmentAssignee.assigned_by_user_id",
    )


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(100), nullable=False, index=True)
    owner_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    owner = relationship(
        "User",
        back_populates="owned_workspaces",
        foreign_keys=[owner_id],
    )
    members = relationship(
        "WorkspaceMember",
        back_populates="workspace",
        cascade="all, delete-orphan",
    )
    invites = relationship(
        "WorkspaceInvite",
        back_populates="workspace",
        cascade="all, delete-orphan",
    )
    products = relationship(
        "Product",
        back_populates="workspace",
    )
    audit_logs = relationship(
        "AuditLog",
        back_populates="workspace",
    )
    categories = relationship(
        "Category",
        back_populates="workspace",
    )
    stock_movements = relationship(
        "StockMovement",
        back_populates="workspace",
    )
    replenishment_requests = relationship(
        "ReplenishmentRequest",
        back_populates="workspace",
    )


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "user_id",
            name="uq_workspace_members_workspace_user",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(
        Integer,
        ForeignKey("workspaces.id"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    role = Column(String(20), nullable=False)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    workspace = relationship(
        "Workspace",
        back_populates="members",
    )
    user = relationship(
        "User",
        back_populates="workspace_memberships",
    )

    @property
    def user_name(self):
        if self.user is None:
            return None

        return self.user.name

    @property
    def user_email(self):
        if self.user is None:
            return None

        return self.user.email

class WorkspaceInvite(Base):
    __tablename__ = "workspace_invites"
    __table_args__ = (
        Index(
            "uq_workspace_invites_pending_email",
            "workspace_id",
            "email",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(
        Integer,
        ForeignKey("workspaces.id"),
        nullable=False,
        index=True,
    )
    email = Column(String(255), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    token = Column(String(255), nullable=False, unique=True, index=True)
    status = Column(String(20), nullable=False, default="pending", index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_by_user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    accepted_by_user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    accepted_at = Column(DateTime(timezone=True), nullable=True)

    workspace = relationship(
        "Workspace",
        back_populates="invites",
    )
    created_by_user = relationship(
        "User",
        back_populates="created_workspace_invites",
        foreign_keys=[created_by_user_id],
    )
    accepted_by_user = relationship(
        "User",
        back_populates="accepted_workspace_invites",
        foreign_keys=[accepted_by_user_id],
    )

    @property
    def invite_url(self):
        return f"/invites/{self.token}/accept"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(
        Integer,
        ForeignKey("workspaces.id"),
        nullable=True,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )
    action = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(100), nullable=False, index=True)
    entity_id = Column(Integer, nullable=True, index=True)
    metadata_json = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    workspace = relationship(
        "Workspace",
        back_populates="audit_logs",
    )
    user = relationship(
        "User",
        back_populates="audit_logs",
    )


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, index=True)

    product_id = Column(
        Integer,
        ForeignKey("products.id"),
        nullable=False,
        index=True,
    )
    workspace_id = Column(
        Integer,
        ForeignKey("workspaces.id"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )

    movement_type = Column(String(20), nullable=False)

    quantity = Column(Integer, nullable=False)
    quantity_before = Column(Integer, nullable=False)
    quantity_after = Column(Integer, nullable=False)

    reason = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    product = relationship(
        "Product",
        back_populates="stock_movements",
    )
    workspace = relationship(
        "Workspace",
        back_populates="stock_movements",
    )
    user = relationship(
        "User",
        back_populates="stock_movements",
    )

    @property
    def user_name(self):
        if self.user is None:
            return None

        return self.user.name

    @property
    def user_email(self):
        if self.user is None:
            return None

        return self.user.email

    @property
    def product_name(self):
        if self.product is None:
            return None

        return self.product.name


class ReplenishmentRequest(Base):
    __tablename__ = "replenishment_requests"
    __table_args__ = (
        CheckConstraint(
            "type IN ('purchase', 'production')",
            name="ck_replenishment_requests_type",
        ),
        CheckConstraint(
            (
                "status IN "
                "('open', 'in_progress', 'completed', 'stocked', 'canceled')"
            ),
            name="ck_replenishment_requests_status",
        ),
        CheckConstraint(
            "quantity_needed > 0",
            name="ck_replenishment_requests_quantity_needed_positive",
        ),
        Index(
            "ix_replenishment_requests_workspace_status",
            "workspace_id",
            "status",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(
        Integer,
        ForeignKey("workspaces.id"),
        nullable=False,
        index=True,
    )
    product_id = Column(
        Integer,
        ForeignKey("products.id"),
        nullable=False,
        index=True,
    )
    created_by_user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    assigned_to_user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )
    type = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="open", index=True)
    quantity_needed = Column(Integer, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)

    workspace = relationship(
        "Workspace",
        back_populates="replenishment_requests",
    )
    product = relationship(
        "Product",
        back_populates="replenishment_requests",
    )
    created_by_user = relationship(
        "User",
        back_populates="created_replenishment_requests",
        foreign_keys=[created_by_user_id],
    )
    assigned_to_user = relationship(
        "User",
        back_populates="assigned_replenishment_requests",
        foreign_keys=[assigned_to_user_id],
    )
    assignees = relationship(
        "ReplenishmentAssignee",
        back_populates="replenishment",
        cascade="all, delete-orphan",
        order_by="ReplenishmentAssignee.created_at.asc()",
    )

    @property
    def product_name(self):
        return self.product.name if self.product else None

    @property
    def product_category(self):
        return self.product.category if self.product else None

    @property
    def current_quantity(self):
        return self.product.quantity if self.product else None

    @property
    def minimum_quantity(self):
        return self.product.minimum_quantity if self.product else None

    @property
    def created_by_name(self):
        return self.created_by_user.name if self.created_by_user else None

    @property
    def assigned_to_name(self):
        return self.assigned_to_user.name if self.assigned_to_user else None


class ReplenishmentAssignee(Base):
    __tablename__ = "replenishment_assignees"
    __table_args__ = (
        UniqueConstraint(
            "replenishment_id",
            "user_id",
            name="uq_replenishment_assignees_request_user",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    replenishment_id = Column(
        Integer,
        ForeignKey("replenishment_requests.id"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    assigned_by_user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    replenishment = relationship(
        "ReplenishmentRequest",
        back_populates="assignees",
    )
    user = relationship(
        "User",
        back_populates="replenishment_assignments",
        foreign_keys=[user_id],
    )
    assigned_by_user = relationship(
        "User",
        back_populates="created_replenishment_assignments",
        foreign_keys=[assigned_by_user_id],
    )

    @property
    def name(self):
        return self.user.name if self.user else None

    @property
    def email(self):
        return self.user.email if self.user else None

    @property
    def role(self):
        if not self.replenishment or not self.replenishment.workspace:
            return None

        membership = next(
            (
                member
                for member in self.replenishment.workspace.members
                if member.user_id == self.user_id
            ),
            None,
        )

        return membership.role if membership else None
