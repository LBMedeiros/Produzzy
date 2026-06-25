from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_categories_workspace_name"),
    )

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(
        Integer,
        ForeignKey("workspaces.id"),
        nullable=True,
        index=True,
    )

    name = Column(String(100), nullable=False, index=True)
    description = Column(String(255), nullable=True)

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


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_products_workspace_name"),
    )

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(
        Integer,
        ForeignKey("workspaces.id"),
        nullable=True,
        index=True,
    )

    name = Column(String(100), nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)

    quantity = Column(Integer, nullable=False, default=0)
    minimum_quantity = Column(Integer, nullable=False, default=0)

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
    stock_movements = relationship(
        "StockMovement",
        back_populates="product",
        cascade="all, delete-orphan",
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
    categories = relationship(
        "Category",
        back_populates="workspace",
    )
    stock_movements = relationship(
        "StockMovement",
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
        nullable=True,
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
