from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import math

from app.core.database import get_async_db
from app.core.security import verify_api_key
from app.api.v1.schemas import (
    OrganizationSchema, OrganizationListSchema, OrganizationCreate, OrganizationUpdate,
    BuildingSchema, BuildingCreate,
    ActivitySchema, ActivityCreate,
    GeoSearchSchema, SearchFilters, PaginatedResponse, ErrorResponse
)
from app.api.v1.services.organization_service import OrganizationService
from app.api.v1.services.building_service import BuildingService
from app.api.v1.services.activity_service import ActivityService


router = APIRouter()



@router.get(
    "/organizations/",
    response_model=PaginatedResponse,
    summary="Список организаций",
    description="Получить список всех организаций с возможностью фильтрации и пагинации"
)
async def get_organizations(
    page: int = Query(1, ge=1, description="Номер страницы"),
    per_page: int = Query(10, ge=1, le=100, description="Количество элементов на странице"),
    building_id: Optional[int] = Query(None, description="Фильтр по ID здания"),
    activity_id: Optional[int] = Query(None, description="Фильтр по ID вида деятельности"),
    name_query: Optional[str] = Query(None, description="Поиск по названию"),
    include_child_activities: bool = Query(True, description="Включать дочерние виды деятельности"),
    db: AsyncSession = Depends(get_async_db),
    api_key: str = Depends(verify_api_key)
):
    service = OrganizationService(db)
    skip = (page - 1) * per_page
    
    filters = SearchFilters(
        building_id=building_id,
        activity_id=activity_id,
        name_query=name_query,
        include_child_activities=include_child_activities
    )
    
    if building_id:
        organizations = await service.get_organizations_by_building(building_id, skip, per_page)
    elif activity_id:
        organizations = await service.get_organizations_by_activity(
            activity_id, include_child_activities, skip, per_page
        )
    elif name_query:
        organizations = await service.search_organizations_by_name(name_query, skip, per_page)
    else:
        organizations = await service.get_all_organizations(skip, per_page)
    

    total = await service.get_organizations_count(filters)
    pages = math.ceil(total / per_page)
    

    items = [
        OrganizationListSchema(
            id=org.id,
            name=org.name,
            building_address=org.building.address if org.building else "Адрес не указан",
            phone_count=len(org.phones) if org.phones else 0
        )
        for org in organizations
    ]
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages
    )


@router.get(
    "/organizations/{org_id}",
    response_model=OrganizationSchema,
    summary="Информация об организации",
    description="Получить полную информацию об организации по её ID"
)
async def get_organization(
    org_id: int,
    db: AsyncSession = Depends(get_async_db),
    api_key: str = Depends(verify_api_key)
):
    service = OrganizationService(db)
    organization = await service.get_organization_by_id(org_id)
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Организация не найдена"
        )
    
    return organization


@router.get(
    "/organizations/by-building/{building_id}",
    response_model=List[OrganizationSchema],
    summary="Организации в здании",
    description="Получить список всех организаций в конкретном здании"
)
async def get_organizations_by_building(
    building_id: int,
    skip: int = Query(0, ge=0, description="Пропустить элементов"),
    limit: int = Query(100, ge=1, le=100, description="Максимальное количество элементов"),
    db: AsyncSession = Depends(get_async_db),
    api_key: str = Depends(verify_api_key)
):
    service = OrganizationService(db)
    organizations = await service.get_organizations_by_building(building_id, skip, limit)
    return organizations


@router.get(
    "/organizations/by-activity/{activity_id}",
    response_model=List[OrganizationSchema],
    summary="Организации по виду деятельности",
    description="Получить организации, относящиеся к указанному виду деятельности"
)
async def get_organizations_by_activity(
    activity_id: int,
    include_children: bool = Query(True, description="Включать дочерние виды деятельности"),
    skip: int = Query(0, ge=0, description="Пропустить элементов"),
    limit: int = Query(100, ge=1, le=100, description="Максимальное количество элементов"),
    db: AsyncSession = Depends(get_async_db),
    api_key: str = Depends(verify_api_key)
):
    service = OrganizationService(db)
    organizations = await service.get_organizations_by_activity(activity_id, include_children, skip, limit)
    return organizations


@router.get(
    "/search",
    response_model=List[OrganizationSchema],
    summary="Поиск организаций по названию",
    description="Найти организации по названию (частичное совпадение)"
)
async def search_organizations(
    q: str = Query(..., description="Поисковый запрос"),
    skip: int = Query(0, ge=0, description="Пропустить элементов"),
    limit: int = Query(100, ge=1, le=100, description="Максимальное количество элементов"),
    db: AsyncSession = Depends(get_async_db),
    api_key: str = Depends(verify_api_key)
):
    service = OrganizationService(db)
    organizations = await service.search_organizations_by_name(q, skip, limit)
    return organizations


@router.post(
    "/organizations/geo-search",
    response_model=List[OrganizationSchema],
    summary="Географический поиск организаций",
    description="Найти организации в заданном радиусе или прямоугольной области"
)
async def geo_search_organizations(
    geo_search: GeoSearchSchema,
    skip: int = Query(0, ge=0, description="Пропустить элементов"),
    limit: int = Query(100, ge=1, le=100, description="Максимальное количество элементов"),
    db: AsyncSession = Depends(get_async_db),
    api_key: str = Depends(verify_api_key)
):
    service = OrganizationService(db)
    organizations = await service.geo_search_organizations(geo_search, skip, limit)
    return organizations


@router.post(
    "/organizations/",
    response_model=OrganizationSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Создать организацию",
    description="Создать новую организацию"
)
async def create_organization(
    organization: OrganizationCreate,
    db: AsyncSession = Depends(get_async_db),
    api_key: str = Depends(verify_api_key)
):
    try:
        service = OrganizationService(db)
        return await service.create_organization(organization)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put(
    "/organizations/{org_id}",
    response_model=OrganizationSchema,
    summary="Обновить организацию",
    description="Обновить данные организации"
)
async def update_organization(
    org_id: int,
    organization: OrganizationUpdate,
    db: AsyncSession = Depends(get_async_db),
    api_key: str = Depends(verify_api_key)
):
    try:
        service = OrganizationService(db)
        updated_org = await service.update_organization(org_id, organization)
        
        if not updated_org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Организация не найдена"
            )
        
        return updated_org
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete(
    "/organizations/{org_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить организацию",
    description="Удалить организацию по ID"
)
async def delete_organization(
    org_id: int,
    db: AsyncSession = Depends(get_async_db),
    api_key: str = Depends(verify_api_key)
):
    service = OrganizationService(db)
    deleted = await service.delete_organization(org_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Организация не найдена"
        )



@router.get(
    "/buildings/",
    response_model=List[BuildingSchema],
    summary="Список зданий",
    description="Получить список всех зданий"
)
async def get_buildings(
    skip: int = Query(0, ge=0, description="Пропустить элементов"),
    limit: int = Query(100, ge=1, le=100, description="Максимальное количество элементов"),
    db: AsyncSession = Depends(get_async_db),
    api_key: str = Depends(verify_api_key)
):
    service = BuildingService(db)
    buildings = await service.get_buildings(skip, limit)
    return buildings


@router.get(
    "/buildings/{building_id}",
    response_model=BuildingSchema,
    summary="Информация о здании",
    description="Получить информацию о здании по ID"
)
async def get_building(
    building_id: int,
    db: AsyncSession = Depends(get_async_db),
    api_key: str = Depends(verify_api_key)
):
    service = BuildingService(db)
    building = await service.get_building_by_id(building_id)
    
    if not building:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Здание не найдено"
        )
    
    return building


@router.post(
    "/buildings/",
    response_model=BuildingSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Создать здание",
    description="Создать новое здание"
)
async def create_building(
    building: BuildingCreate,
    db: AsyncSession = Depends(get_async_db),
    api_key: str = Depends(verify_api_key)
):
    try:
        service = BuildingService(db)
        return await service.create_building(building)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete(
    "/buildings/{building_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить здание",
    description="Удалить здание по ID"
)
async def delete_building(
    building_id: int,
    db: AsyncSession = Depends(get_async_db),
    api_key: str = Depends(verify_api_key)
):
    try:
        service = BuildingService(db)
        deleted = await service.delete_building(building_id)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Здание не найдено"
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )



@router.get(
    "/activities/",
    response_model=List[ActivitySchema],
    summary="Список видов деятельности",
    description="Получить список всех видов деятельности в виде дерева"
)
async def get_activities(
    parent_id: Optional[int] = Query(None, description="ID родительской деятельности (для получения дочерних)"),
    level: Optional[int] = Query(None, ge=1, le=3, description="Уровень деятельности (1-3)"),
    db: AsyncSession = Depends(get_async_db),
    api_key: str = Depends(verify_api_key)
):
    service = ActivityService(db)
    activities = await service.get_activities(parent_id, level)
    return activities


@router.get(
    "/activities/{activity_id}",
    response_model=ActivitySchema,
    summary="Информация о виде деятельности",
    description="Получить информацию о виде деятельности по ID"
)
async def get_activity(
    activity_id: int,
    db: AsyncSession = Depends(get_async_db),
    api_key: str = Depends(verify_api_key)
):
    service = ActivityService(db)
    activity = await service.get_activity_by_id(activity_id)
    
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вид деятельности не найден"
        )
    
    return activity


@router.get(
    "/tree",
    response_model=List[ActivitySchema],
    summary="Дерево видов деятельности",
    description="Получить полное дерево видов деятельности"
)
async def get_activities_tree(
    db: AsyncSession = Depends(get_async_db),
    api_key: str = Depends(verify_api_key)
):
    service = ActivityService(db)
    tree = await service.get_activities_tree()
    return tree


@router.post(
    "/activities/",
    response_model=ActivitySchema,
    status_code=status.HTTP_201_CREATED,
    summary="Создать вид деятельности",
    description="Создать новый вид деятельности"
)
async def create_activity(
    activity: ActivityCreate,
    db: AsyncSession = Depends(get_async_db),
    api_key: str = Depends(verify_api_key)
):
    try:
        service = ActivityService(db)
        return await service.create_activity(activity)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete(
    "/activities/{activity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить вид деятельности",
    description="Удалить вид деятельности по ID"
)
async def delete_activity(
    activity_id: int,
    db: AsyncSession = Depends(get_async_db),
    api_key: str = Depends(verify_api_key)
):
    try:
        service = ActivityService(db)
        deleted = await service.delete_activity(activity_id)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Вид деятельности не найден"
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )