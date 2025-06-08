from sqlalchemy import Column, Integer, String, Float, ForeignKey, Table, Index
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(AsyncAttrs, DeclarativeBase):
    pass


organization_activity = Table(
    'organization_activity',
    Base.metadata,
    Column('organization_id', Integer, ForeignKey('organizations.id'), primary_key=True),
    Column('activity_id', Integer, ForeignKey('activities.id'), primary_key=True)
)

class Building(Base):
    """Модель здания"""
    __tablename__ = 'buildings'

    id = Column(Integer, primary_key=True, index=True)
    address = Column(String(500), nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)


    organizations = relationship(
        "Organization",
        back_populates="building",
        lazy="selectin"
    )

    __table_args__ = (
        Index('idx_coordinates', 'latitude', 'longitude'),
    )

    def __repr__(self):
        return f"<Building(address='{self.address}')>"

class Activity(Base):
    """Модель вида деятельности с древовидной структурой"""
    __tablename__ = 'activities'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey('activities.id'), nullable=True)
    level = Column(Integer, nullable=False, default=1)


    parent = relationship(
        "Activity",
        remote_side=[id],
        back_populates="children",
        lazy="selectin"
    )


    children = relationship(
        "Activity",
        back_populates="parent",
        lazy="selectin"
    )


    organizations = relationship(
        "Organization",
        secondary=organization_activity,
        back_populates="activities",
        lazy="selectin"
    )

    def __repr__(self):
        return f"<Activity(name='{self.name}', level={self.level})>"

class OrganizationPhone(Base):
    """Модель телефонов организации"""
    __tablename__ = 'organization_phones'

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey('organizations.id'), nullable=False)
    phone_number = Column(String(20), nullable=False)


    organization = relationship(
        "Organization",
        back_populates="phones",
        lazy="selectin"
    )

    def __repr__(self):
        return f"<OrganizationPhone(phone_number='{self.phone_number}')>"

class Organization(Base):
    """Модель организации"""
    __tablename__ = 'organizations'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(300), nullable=False, index=True)
    building_id = Column(Integer, ForeignKey('buildings.id'), nullable=False)


    building = relationship(
        "Building",
        back_populates="organizations",
        lazy="selectin"
    )
    phones = relationship(
        "OrganizationPhone",
        back_populates="organization",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    activities = relationship(
        "Activity",
        secondary=organization_activity,
        back_populates="organizations",
        lazy="selectin"
    )

    def __repr__(self):
        return f"<Organization(name='{self.name}')>"