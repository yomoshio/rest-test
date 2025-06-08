from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional
from enum import Enum



class PhoneSchema(BaseModel):
    """Схема телефона"""
    id: Optional[int] = None
    phone_number: str = Field(..., description="Номер телефона", example="8-923-666-13-13")

    class Config:
        from_attributes = True

class PhoneCreate(BaseModel):
    """Схема для создания телефона"""
    phone_number: str = Field(..., description="Номер телефона", example="8-923-666-13-13")

    @field_validator('phone_number')
    @classmethod
    def validate_phone_number(cls, v: str) -> str:

        if not v.startswith('+') and not v.startswith('8'):
            raise ValueError('Номер телефона должен начинаться с "+" или "8"')
        return v



class BuildingBase(BaseModel):
    """Базовая схема здания"""
    address: str = Field(..., description="Адрес здания", example="г. Москва, ул. Ленина 1, офис 3")
    latitude: float = Field(..., description="Широта", ge=-90, le=90)
    longitude: float = Field(..., description="Долгота", ge=-180, le=180)

class BuildingCreate(BuildingBase):
    """Схема для создания здания"""
    pass

class BuildingSchema(BuildingBase):
    """Схема здания с ID"""
    id: int

    class Config:
        from_attributes = True



class ActivityBase(BaseModel):
    """Базовая схема вида деятельности"""
    name: str = Field(..., description="Название вида деятельности", example="Мясная продукция")
    parent_id: Optional[int] = Field(None, description="ID родительского вида деятельности")
    level: int = Field(default=1, ge=1, le=3, description="Уровень вложенности (1-3)")

class ActivityCreate(ActivityBase):
    """Схема для создания вида деятельности"""
    
    @field_validator('level')
    @classmethod
    def validate_level(cls, v: int) -> int:
        if v < 1 or v > 3:
            raise ValueError('Уровень должен быть от 1 до 3')
        return v

class ActivitySchema(ActivityBase):
    """Схема вида деятельности с ID и дочерними элементами"""
    id: int
    children: Optional[List['ActivitySchema']] = Field(default_factory=list, description="Дочерние виды деятельности")

    class Config:
        from_attributes = True



class OrganizationBase(BaseModel):
    """Базовая схема организации"""
    name: str = Field(..., description="Название организации", example='ООО "Рога и Копыта"')
    building_id: int = Field(..., description="ID здания, где находится организация")

class OrganizationCreate(OrganizationBase):
    """Схема для создания организации"""
    phone_numbers: Optional[List[str]] = Field(default_factory=list, description="Номера телефонов")
    activity_ids: Optional[List[int]] = Field(default_factory=list, description="ID видов деятельности")

class OrganizationUpdate(BaseModel):
    """Схема для обновления организации"""
    name: Optional[str] = Field(None, description="Название организации")
    building_id: Optional[int] = Field(None, description="ID здания")
    phone_numbers: Optional[List[str]] = Field(None, description="Номера телефонов")
    activity_ids: Optional[List[int]] = Field(None, description="ID видов деятельности")


class ActivitySchemaShallow(ActivityBase):
    """Схема вида деятельности без рекурсии"""
    id: int

    class Config:
        from_attributes = True

class OrganizationSchema(BaseModel):
    """Полная схема организации с ограничением рекурсии"""
    id: int
    name: str = Field(..., description="Название организации", example='ООО "Рога и Копыта"')
    building_id: int = Field(..., description="ID здания, где находится организация")
    building: Optional[BuildingSchema] = Field(None, description="Здание организации")
    phones: Optional[List[PhoneSchema]] = Field(default_factory=list, description="Телефоны организации")
    activities: Optional[List[ActivitySchemaShallow]] = Field(default_factory=list, description="Виды деятельности")

    class Config:
        from_attributes = True

class OrganizationListSchema(BaseModel):
    """Схема для списка организаций (краткая информация)"""
    id: int
    name: str
    building_address: str = Field(..., description="Адрес здания")
    phone_count: int = Field(..., description="Количество телефонов")

    class Config:
        from_attributes = True



class GeoSearchType(str, Enum):
    """Тип географического поиска"""
    RADIUS = "radius"
    RECTANGLE = "rectangle"

class GeoSearchSchema(BaseModel):
    """Схема для географического поиска"""
    latitude: float = Field(..., description="Широта центральной точки", ge=-90, le=90)
    longitude: float = Field(..., description="Долгота центральной точки", ge=-180, le=180)
    search_type: GeoSearchType = Field(..., description="Тип поиска: radius или rectangle")
    

    radius_km: Optional[float] = Field(None, description="Радиус поиска в километрах", gt=0)
    

    north_lat: Optional[float] = Field(None, description="Северная широта", ge=-90, le=90)
    south_lat: Optional[float] = Field(None, description="Южная широта", ge=-90, le=90)
    east_lng: Optional[float] = Field(None, description="Восточная долгота", ge=-180, le=180)
    west_lng: Optional[float] = Field(None, description="Западная долгота", ge=-180, le=180)
    
    @model_validator(mode='after')
    def validate_search_parameters(self):
        if self.search_type == GeoSearchType.RADIUS:
            if self.radius_km is None:
                raise ValueError('Для поиска по радиусу необходимо указать radius_km')
        elif self.search_type == GeoSearchType.RECTANGLE:
            required_coords = [self.north_lat, self.south_lat, self.east_lng, self.west_lng]
            if any(coord is None for coord in required_coords):
                raise ValueError('Для поиска по прямоугольнику необходимо указать все координаты')
            if self.north_lat <= self.south_lat:
                raise ValueError('north_lat должен быть больше south_lat')
        return self

class SearchFilters(BaseModel):
    """Схема для фильтров поиска"""
    building_id: Optional[int] = Field(None, description="ID здания")
    activity_id: Optional[int] = Field(None, description="ID вида деятельности")
    name_query: Optional[str] = Field(None, description="Поисковый запрос по названию")
    include_child_activities: bool = Field(True, description="Включать дочерние виды деятельности")



class PaginatedResponse(BaseModel):
    """Схема для пагинированного ответа"""
    items: List[OrganizationListSchema]
    total: int = Field(..., description="Общее количество элементов")
    page: int = Field(..., description="Текущая страница")
    per_page: int = Field(..., description="Элементов на странице")
    pages: int = Field(..., description="Общее количество страниц")

class ErrorResponse(BaseModel):
    """Схема для ошибок"""
    detail: str = Field(..., description="Описание ошибки")


ActivitySchema.model_rebuild()