from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import func, and_, select
from typing import List, Optional
from app.models.models import Activity, Organization
from app.api.v1.schemas import ActivityCreate


class ActivityService:
    """Сервис для работы с видами деятельности"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_activity_by_id(self, activity_id: int) -> Optional[Activity]:
        """Получить вид деятельности по ID"""
        query = select(Activity).options(
            selectinload(Activity.children).selectinload(Activity.children).selectinload(Activity.children),  # Load up to 3 levels
            selectinload(Activity.parent),
            selectinload(Activity.organizations)
        ).where(Activity.id == activity_id)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_activity_tree(self) -> List[Activity]:
        """Получить дерево видов деятельности (только корневые элементы с детьми)"""
        query = select(Activity).options(
            selectinload(Activity.children).selectinload(Activity.children).selectinload(Activity.children)  # Load up to 3 levels
        ).where(Activity.parent_id.is_(None)).order_by(Activity.name)
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_activities_tree(self) -> List[Activity]:
        """Получить полное дерево видов деятельности"""
        query = select(Activity).options(
            selectinload(Activity.children).selectinload(Activity.children).selectinload(Activity.children)  # Load up to 3 levels
        ).order_by(Activity.level, Activity.name)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_activities(self, parent_id: Optional[int] = None, level: Optional[int] = None) -> List[Activity]:
        """Получить виды деятельности с возможностью фильтрации по родителю и уровню"""
        query = select(Activity).options(
            selectinload(Activity.children).selectinload(Activity.children).selectinload(Activity.children),  # Load up to 3 levels
            selectinload(Activity.parent)
        )
        
        if parent_id is not None:
            query = query.where(Activity.parent_id == parent_id)
        elif level is not None:
            query = query.where(Activity.level == level)
        else:
            query = query.where(Activity.parent_id.is_(None))
        
        query = query.order_by(Activity.level, Activity.name)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def _load_children(self, activity: Activity, depth: int = 3):
        """Рекурсивно загружаем дочерние элементы до указанной глубины"""
        if depth <= 0:
            return
        
        query = select(Activity).options(
            selectinload(Activity.children)
        ).where(Activity.parent_id == activity.id)
        result = await self.db.execute(query)
        activity.children = result.scalars().all()
        
        for child in activity.children:
            await self._load_children(child, depth - 1)
    
    async def get_all_activities(self, level: Optional[int] = None, skip: int = 0, limit: int = 100) -> List[Activity]:
        """Получить все виды деятельности с возможностью фильтрации по уровню"""
        query = select(Activity).options(
            selectinload(Activity.children),
            selectinload(Activity.parent)
        )
        
        if level is not None:
            query = query.where(Activity.level == level)
        
        query = query.order_by(Activity.level, Activity.name).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_root_activities(self) -> List[Activity]:
        """Получить корневые виды деятельности (уровень 1)"""
        query = select(Activity).options(
            selectinload(Activity.children).selectinload(Activity.children)
        ).where(Activity.parent_id.is_(None)).order_by(Activity.name)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_children_activities(self, parent_id: int) -> List[Activity]:
        """Получить дочерние виды деятельности"""
        query = select(Activity).options(
            selectinload(Activity.children)
        ).where(Activity.parent_id == parent_id).order_by(Activity.name)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def create_activity(self, activity_data: ActivityCreate) -> Activity:
        """Создать новый вид деятельности"""
        # Проверяем ограничения уровня вложенности
        if activity_data.parent_id:
            parent_query = select(Activity).where(Activity.id == activity_data.parent_id)
            parent_result = await self.db.execute(parent_query)
            parent = parent_result.scalar_one_or_none()
            
            if not parent:
                raise ValueError("Родительский вид деятельности не найден")
            
            if parent.level >= 3:
                raise ValueError("Достигнут максимальный уровень вложенности (3 уровня)")
            
            activity_data.level = parent.level + 1
        else:
            activity_data.level = 1
        
        # Проверяем уникальность названия на том же уровне с тем же родителем
        existing_query = select(Activity).where(
            and_(
                Activity.name == activity_data.name,
                Activity.parent_id == activity_data.parent_id
            )
        )
        existing_result = await self.db.execute(existing_query)
        existing = existing_result.scalar_one_or_none()
        
        if existing:
            raise ValueError("Вид деятельности с таким названием уже существует на этом уровне")
        
        activity = Activity(
            name=activity_data.name,
            parent_id=activity_data.parent_id,
            level=activity_data.level
        )
        
        self.db.add(activity)
        await self.db.commit()
        await self.db.refresh(activity)
        return activity
    
    async def update_activity(self, activity_id: int, activity_data: ActivityCreate) -> Optional[Activity]:
        """Обновить вид деятельности"""
        query = select(Activity).where(Activity.id == activity_id)
        result = await self.db.execute(query)
        activity = result.scalar_one_or_none()
        
        if not activity:
            return None
        
        # Проверяем, не создается ли циклическая зависимость
        if activity_data.parent_id:
            if await self._would_create_cycle(activity_id, activity_data.parent_id):
                raise ValueError("Обновление создаст циклическую зависимость")
            
            parent_query = select(Activity).where(Activity.id == activity_data.parent_id)
            parent_result = await self.db.execute(parent_query)
            parent = parent_result.scalar_one_or_none()
            
            if not parent:
                raise ValueError("Родительский вид деятельности не найден")
            
            if parent.level >= 3:
                raise ValueError("Достигнут максимальный уровень вложенности (3 уровня)")
            
            activity.level = parent.level + 1
        else:
            activity.level = 1
        
        # Проверяем уникальность названия
        existing_query = select(Activity).where(
            and_(
                Activity.name == activity_data.name,
                Activity.parent_id == activity_data.parent_id,
                Activity.id != activity_id
            )
        )
        existing_result = await self.db.execute(existing_query)
        existing = existing_result.scalar_one_or_none()
        
        if existing:
            raise ValueError("Вид деятельности с таким названием уже существует на этом уровне")
        
        activity.name = activity_data.name
        activity.parent_id = activity_data.parent_id
        
        # Обновляем уровни всех дочерних элементов
        await self._update_children_levels(activity_id)
        
        await self.db.commit()
        await self.db.refresh(activity)
        return activity
    
    async def delete_activity(self, activity_id: int) -> bool:
        """Удалить вид деятельности"""
        query = select(Activity).where(Activity.id == activity_id)
        result = await self.db.execute(query)
        activity = result.scalar_one_or_none()
        
        if not activity:
            return False
        
        # Проверяем, есть ли связанные организации
        org_count_query = select(func.count(Organization.id)).join(
            Organization.activities
        ).where(Activity.id == activity_id)
        org_count_result = await self.db.execute(org_count_query)
        org_count = org_count_result.scalar()
        
        if org_count > 0:
            raise ValueError("Нельзя удалить вид деятельности, к которому привязаны организации")
        
        # Проверяем, есть ли дочерние элементы
        children_count_query = select(func.count(Activity.id)).where(
            Activity.parent_id == activity_id
        )
        children_count_result = await self.db.execute(children_count_query)
        children_count = children_count_result.scalar()
        
        if children_count > 0:
            raise ValueError("Нельзя удалить вид деятельности, у которого есть дочерние элементы")
        
        await self.db.delete(activity)
        await self.db.commit()
        return True
    
    async def get_activity_path(self, activity_id: int) -> List[Activity]:
        """Получить путь от корня до указанного вида деятельности"""
        activity = await self.get_activity_by_id(activity_id)
        if not activity:
            return []
        
        path = [activity]
        current = activity
        
        while current.parent_id:
            parent = await self.get_activity_by_id(current.parent_id)
            if parent:
                path.insert(0, parent)
                current = parent
            else:
                break
        
        return path
    
    async def search_activities_by_name(self, name_query: str, skip: int = 0, limit: int = 100) -> List[Activity]:
        """Поиск видов деятельности по названию"""
        query = select(Activity).options(
            selectinload(Activity.children),
            selectinload(Activity.parent)
        ).where(Activity.name.ilike(f"%{name_query}%")).order_by(
            Activity.level, Activity.name
        ).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_activities_count(self, level: Optional[int] = None) -> int:
        """Получить количество видов деятельности"""
        query = select(func.count(Activity.id))
        if level is not None:
            query = query.where(Activity.level == level)
        
        result = await self.db.execute(query)
        return result.scalar()
    
    async def _would_create_cycle(self, activity_id: int, new_parent_id: int) -> bool:
        """Проверяет, создаст ли изменение родителя циклическую зависимость"""
        current_id = new_parent_id
        
        while current_id:
            if current_id == activity_id:
                return True
            
            query = select(Activity.parent_id).where(Activity.id == current_id)
            result = await self.db.execute(query)
            parent = result.scalar_one_or_none()
            current_id = parent if parent else None
        
        return False
    
    async def _update_children_levels(self, parent_id: int):
        """Рекурсивно обновляет уровни всех дочерних элементов"""
        parent_query = select(Activity).where(Activity.id == parent_id)
        parent_result = await self.db.execute(parent_query)
        parent = parent_result.scalar_one_or_none()
        
        if not parent:
            return
        
        children_query = select(Activity).where(Activity.parent_id == parent_id)
        children_result = await self.db.execute(children_query)
        children = children_result.scalars().all()
        
        for child in children:
            new_level = parent.level + 1
            if new_level <= 3:  
                child.level = new_level
                await self._update_children_levels(child.id)
            else:
                raise ValueError(f"Обновление уровня для активности '{child.name}' превысит максимальную глубину")