from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import func, select
from typing import List, Optional
from app.models.models import Building, Organization
from app.api.v1.schemas import BuildingCreate
from app.utils.geo_utils import validate_coordinates


class BuildingService:
    """Сервис для работы со зданиями"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_building_by_id(self, building_id: int) -> Optional[Building]:
        """Получить здание по ID"""
        query = select(Building).options(
            selectinload(Building.organizations)
        ).where(Building.id == building_id)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_buildings(self, skip: int = 0, limit: int = 100) -> List[Building]:
        """Получить список всех зданий"""
        query = select(Building).options(
            selectinload(Building.organizations)
        ).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_all_buildings(self, skip: int = 0, limit: int = 100) -> List[Building]:
        """Получить список всех зданий (алиас для get_buildings)"""
        return await self.get_buildings(skip, limit)
    
    async def get_buildings_with_organizations_count(self, skip: int = 0, limit: int = 100) -> List[dict]:
        """Получить здания с количеством организаций"""
        query = select(
            Building,
            func.count(Organization.id).label('organizations_count')
        ).outerjoin(Building.organizations).group_by(Building.id).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        rows = result.all()
        
        return [
            {
                'building': building,
                'organizations_count': count
            }
            for building, count in rows
        ]
    
    async def create_building(self, building_data: BuildingCreate) -> Building:
        """Создать новое здание"""
        if not validate_coordinates(building_data.latitude, building_data.longitude):
            raise ValueError("Некорректные координаты")
        
        building = Building(
            address=building_data.address,
            latitude=building_data.latitude,
            longitude=building_data.longitude
        )
        
        self.db.add(building)
        await self.db.commit()
        await self.db.refresh(building)
        return building
    
    async def update_building(self, building_id: int, building_data: BuildingCreate) -> Optional[Building]:
        """Обновить здание"""
        if not validate_coordinates(building_data.latitude, building_data.longitude):
            raise ValueError("Некорректные координаты")
        
        query = select(Building).where(Building.id == building_id)
        result = await self.db.execute(query)
        building = result.scalar_one_or_none()
        
        if not building:
            return None
        
        building.address = building_data.address
        building.latitude = building_data.latitude
        building.longitude = building_data.longitude
        
        await self.db.commit()
        await self.db.refresh(building)
        return building
    
    async def delete_building(self, building_id: int) -> bool:
        """Удалить здание (только если в нем нет организаций)"""
        query = select(Building).where(Building.id == building_id)
        result = await self.db.execute(query)
        building = result.scalar_one_or_none()
        
        if not building:
            return False
        
        # Проверяем, есть ли организации в здании
        org_count_query = select(func.count(Organization.id)).where(
            Organization.building_id == building_id
        )
        org_count_result = await self.db.execute(org_count_query)
        org_count = org_count_result.scalar()
        
        if org_count > 0:
            raise ValueError("Нельзя удалить здание, в котором есть организации")
        
        await self.db.delete(building)
        await self.db.commit()
        return True
    
    async def get_buildings_count(self) -> int:
        """Получить общее количество зданий"""
        query = select(func.count(Building.id))
        result = await self.db.execute(query)
        return result.scalar()
    
    async def search_buildings_by_address(self, address_query: str, skip: int = 0, limit: int = 100) -> List[Building]:
        """Поиск зданий по адресу"""
        query = select(Building).where(
            Building.address.ilike(f"%{address_query}%")
        ).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()