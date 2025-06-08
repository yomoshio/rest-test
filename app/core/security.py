from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.security.api_key import APIKeyHeader
from .config import settings


api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Depends(api_key_header)) -> str:
    """
    Проверка API ключа из заголовка X-API-Key.
    
    Args:
        api_key: API ключ из заголовка запроса
        
    Returns:
        str: Валидный API ключ
        
    Raises:
        HTTPException: Если API ключ неверный или отсутствует
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API ключ отсутствует. Добавьте заголовок X-API-Key"
        )
    
    if api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный API ключ"
        )
    
    return api_key