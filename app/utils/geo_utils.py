import math
from typing import Tuple, List
from geopy.distance import geodesic




def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Вычисляет расстояние между двумя точками в километрах.
    
    Args:
        lat1, lon1: Координаты первой точки
        lat2, lon2: Координаты второй точки
        
    Returns:
        float: Расстояние в километрах
    """
    point1 = (lat1, lon1)
    point2 = (lat2, lon2)
    return geodesic(point1, point2).kilometers


def get_bounding_box(latitude: float, longitude: float, radius_km: float) -> Tuple[float, float, float, float]:
    """
    Вычисляет границы прямоугольника для поиска по радиусу.
    
    Args:
        latitude: Широта центральной точки
        longitude: Долгота центральной точки
        radius_km: Радиус в километрах
        
    Returns:
        Tuple[float, float, float, float]: (min_lat, max_lat, min_lon, max_lon)
    """

    lat_offset = radius_km / 111.0
    

    lon_offset = radius_km / (111.0 * math.cos(math.radians(latitude)))
    
    min_lat = latitude - lat_offset
    max_lat = latitude + lat_offset
    min_lon = longitude - lon_offset
    max_lon = longitude + lon_offset
    
    return min_lat, max_lat, min_lon, max_lon


def point_in_rectangle(lat: float, lon: float, north: float, south: float, 
                      east: float, west: float) -> bool:
    """
    Проверяет, находится ли точка в прямоугольной области.
    
    Args:
        lat, lon: Координаты точки
        north, south, east, west: Границы прямоугольника
        
    Returns:
        bool: True, если точка находится в области
    """
    return south <= lat <= north and west <= lon <= east


def validate_coordinates(latitude: float, longitude: float) -> bool:
    """
    Проверяет корректность координат.
    
    Args:
        latitude: Широта
        longitude: Долгота
        
    Returns:
        bool: True, если координаты корректны
    """
    return -90 <= latitude <= 90 and -180 <= longitude <= 180