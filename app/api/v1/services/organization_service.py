from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import func, select, and_, or_
from typing import List, Optional
from app.models.models import organization_activity
from app.models.models import Organization, Building, Activity, OrganizationPhone
from app.api.v1.schemas import (
    OrganizationCreate, OrganizationUpdate, GeoSearchSchema, SearchFilters
)
from app.utils.geo_utils import calculate_distance


class OrganizationService:
    """Сервис для работы с организациями"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_organization_by_id(self, org_id: int) -> Optional[Organization]:
        """Получить организацию по ID"""
        query = select(Organization).options(
            selectinload(Organization.building),
            selectinload(Organization.activities).selectinload(Activity.children).selectinload(Activity.children),  # Load children up to 2 levels
            selectinload(Organization.phones)
        ).where(Organization.id == org_id)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
        
    async def get_all_organizations(self, skip: int = 0, limit: int = 100) -> List[Organization]:
        query = select(Organization).options(
            selectinload(Organization.building),
            selectinload(Organization.activities).selectinload(Activity.children).selectinload(Activity.children),
            selectinload(Organization.phones)
        ).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_organizations_by_building(self, building_id: int, skip: int = 0, limit: int = 100) -> List[Organization]:
        query = select(Organization).options(
            selectinload(Organization.building),
            selectinload(Organization.activities).selectinload(Activity.children).selectinload(Activity.children),
            selectinload(Organization.phones)
        ).where(Organization.building_id == building_id).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
        
    async def get_organizations_by_activity(
        self, 
        activity_id: int, 
        include_children: bool = True, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Organization]:
        """Получить организации по виду деятельности"""
        if include_children:
            activity_ids = await self._get_activity_with_children(activity_id)
        else:
            activity_ids = [activity_id]
        
        query = select(Organization).options(
            selectinload(Organization.building),
            selectinload(Organization.activities).selectinload(Activity.children).selectinload(Activity.children),  # Load children
            selectinload(Organization.phones)
        ).join(Organization.activities).where(
            Activity.id.in_(activity_ids)
        ).distinct().offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def search_organizations_by_name(self, name_query: str, skip: int = 0, limit: int = 100) -> List[Organization]:
        """Поиск организаций по названию"""
        # Экранируем специальные символы в поисковом запросе для безопасности
        safe_query = name_query.replace('%', r'\%').replace('_', r'\_')
        query = (
            select(Organization)
            .options(
                selectinload(Organization.building),
                selectinload(Organization.activities).selectinload(Activity.children),  # Предзагружаем children
                selectinload(Organization.phones)
            )
            .where(Organization.name.ilike(f"%{safe_query}%"))
            .offset(skip)
            .limit(limit)
        )

        result = await self.db.execute(query)
        organizations = result.scalars().all()
        return organizations
    
    async def geo_search_organizations(self, geo_search: GeoSearchSchema, skip: int = 0, limit: int = 100) -> List[Organization]:
        query = select(Organization).options(
            selectinload(Organization.building),
            selectinload(Organization.activities).selectinload(Activity.children).selectinload(Activity.children),
            selectinload(Organization.phones)
        ).join(Organization.building)
        
        if geo_search.search_type == "radius" and geo_search.radius_km:
            # Приблизительная фильтрация по прямоугольнику для оптимизации
            lat_delta = geo_search.radius_km / 111.0
            lng_delta = geo_search.radius_km / (111.0 * func.cos(func.radians(geo_search.latitude)))
            
            query = query.where(
                and_(
                    Building.latitude.between(
                        geo_search.latitude - lat_delta,
                        geo_search.latitude + lat_delta
                    ),
                    Building.longitude.between(
                        geo_search.longitude - lng_delta,
                        geo_search.longitude + lng_delta
                    )
                )
            )
        elif geo_search.search_type == "rectangle":
            query = query.where(
                and_(
                    Building.latitude.between(geo_search.south_lat, geo_search.north_lat),
                    Building.longitude.between(geo_search.west_lng, geo_search.east_lng)
                )
            )
        
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        organizations = result.scalars().all()
        
        # Точная фильтрация по радиусу после получения из БД
        if geo_search.search_type == "radius" and geo_search.radius_km:
            filtered_orgs = []
            for org in organizations:
                if org.building:
                    distance = calculate_distance(
                        geo_search.latitude, geo_search.longitude,
                        org.building.latitude, org.building.longitude
                    )
                    if distance <= geo_search.radius_km:
                        filtered_orgs.append(org)
            return filtered_orgs
        
        return organizations
            
    async def create_organization(self, org_data: OrganizationCreate) -> Organization:
        """Создать новую организацию"""
        # Проверяем существование здания
        building_query = select(Building).where(Building.id == org_data.building_id)
        building_result = await self.db.execute(building_query)
        building = building_result.scalar_one_or_none()

        if not building:
            raise ValueError("Здание не найдено")

        # Создаём организацию
        organization = Organization(
            name=org_data.name,
            building_id=org_data.building_id
        )

        self.db.add(organization)
        await self.db.commit()  # Сохраняем организацию в базе данных
        await self.db.refresh(organization)  # Обновляем объект для получения ID

        # Добавляем виды деятельности через ассоциативную таблицу
        if org_data.activity_ids:
            activities_query = select(Activity).where(Activity.id.in_(org_data.activity_ids))
            activities_result = await self.db.execute(activities_query)
            activities = activities_result.scalars().all()

            # Проверяем, что все указанные activity_ids существуют
            if len(activities) != len(org_data.activity_ids):
                raise ValueError("Один или несколько видов деятельности не найдены")

            # Явно добавляем связи в ассоциативную таблицу
            for activity in activities:
                await self.db.execute(
                    organization_activity.insert().values(
                        organization_id=organization.id,
                        activity_id=activity.id
                    )
                )

        # Добавляем телефонные номера
        if org_data.phone_numbers:
            for phone_number in org_data.phone_numbers:
                phone = OrganizationPhone(
                    phone_number=phone_number,
                    organization_id=organization.id
                )
                self.db.add(phone)

        await self.db.commit()
        await self.db.refresh(organization, attribute_names=["activities", "phones"])  # Обновляем связанные данные

        # Загружаем организацию с предзагруженными связями
        return await self.get_organization_by_id(organization.id)

    
    async def update_organization(self, org_id: int, org_data: OrganizationUpdate) -> Optional[Organization]:
        """Обновить организацию"""
        query = select(Organization).where(Organization.id == org_id)
        result = await self.db.execute(query)
        organization = result.scalar_one_or_none()
        
        if not organization:
            return None
        
        # Проверяем здание если оно изменилось
        if org_data.building_id and org_data.building_id != organization.building_id:
            building_query = select(Building).where(Building.id == org_data.building_id)
            building_result = await self.db.execute(building_query)
            building = building_result.scalar_one_or_none()
            
            if not building:
                raise ValueError("Здание не найдено")
            
            organization.building_id = org_data.building_id
        
        # Обновляем название
        if org_data.name:
            organization.name = org_data.name
        
        # Обновляем виды деятельности
        if org_data.activity_ids is not None:
            # Очищаем старые связи
            organization.activities.clear()
            
            # Добавляем новые
            if org_data.activity_ids:
                activities_query = select(Activity).where(Activity.id.in_(org_data.activity_ids))
                activities_result = await self.db.execute(activities_query)
                activities = activities_result.scalars().all()
                organization.activities.extend(activities)
        
        # Обновляем телефоны - исправить на phone_numbers
        if org_data.phone_numbers is not None:
            # Удаляем старые телефоны
            phones_query = select(OrganizationPhone).where(OrganizationPhone.organization_id == org_id)
            phones_result = await self.db.execute(phones_query)
            old_phones = phones_result.scalars().all()
            
            for phone in old_phones:
                await self.db.delete(phone)
            
            # Добавляем новые телефоны
            for phone_number in org_data.phone_numbers:
                phone = OrganizationPhone(phone_number=phone_number, organization_id=org_id)  # Исправить на phone_number
                self.db.add(phone)
        
        await self.db.commit()
        await self.db.refresh(organization)
        
        return await self.get_organization_by_id(org_id)
    
    async def delete_organization(self, org_id: int) -> bool:
        """Удалить организацию"""
        query = select(Organization).where(Organization.id == org_id)
        result = await self.db.execute(query)
        organization = result.scalar_one_or_none()
        
        if not organization:
            return False
        
        # Удаляем связанные телефоны
        phones_query = select(OrganizationPhone).where(OrganizationPhone.organization_id == org_id)
        phones_result = await self.db.execute(phones_query)
        phones = phones_result.scalars().all()
        
        for phone in phones:
            await self.db.delete(phone)
        
        # Удаляем организацию (связи с activities удалятся автоматически через каскад)
        await self.db.delete(organization)
        await self.db.commit()
        return True
    
    async def get_organizations_count(self, filters: Optional[SearchFilters] = None) -> int:
        """Получить количество организаций с учетом фильтров"""
        query = select(func.count(Organization.id))
        
        if filters:
            if filters.building_id:
                query = query.where(Organization.building_id == filters.building_id)
            
            if filters.activity_id:
                if filters.include_child_activities:
                    activity_ids = await self._get_activity_with_children(filters.activity_id)
                else:
                    activity_ids = [filters.activity_id]
                
                query = query.join(Organization.activities).where(Activity.id.in_(activity_ids))
            
            if filters.name_query:
                query = query.where(Organization.name.ilike(f"%{filters.name_query}%"))
        
        result = await self.db.execute(query)
        return result.scalar()
    
    async def _get_activity_with_children(self, activity_id: int) -> List[int]:
        """Получить все ID активностей в дереве (включая дочерние)"""
        async def get_children_recursive(parent_id: int) -> List[int]:
            query = select(Activity.id).where(Activity.parent_id == parent_id)
            result = await self.db.execute(query)
            children_ids = result.scalars().all()
            
            result_ids = list(children_ids)
            for child_id in children_ids:
                child_children = await get_children_recursive(child_id)
                result_ids.extend(child_children)
            
            return result_ids
        
        result = [activity_id]
        children = await get_children_recursive(activity_id)
        result.extend(children)
        return result