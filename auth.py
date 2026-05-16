import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

import db.models as models
from db.database import get_db

security = HTTPBearer()

# Публічний ключ у форматі PEM.
# Його можна знайти в панелі Clerk: API Keys -> Advanced -> JWT Templates -> Signing Key (PEM public key)
CLERK_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAuk2w8CZzG7su1jR3yeWl
hGiHK3gImpdM+c43E61l1JgOuCOKRlMr3WPC2WFSC7c5Q8f/BBi3uOurK7FjlE1v
R2atIHgPz0d56ihwrIlMLo/fM484fQ7pLm+OQxKLjIiCxxWnT3W7cs3WDXlZUhTO
fYJwf4dJrTG4VqgVOXirn28PpYKRXwqvKIs9kbL9jA8JGMuwJVnlz7kNc0OjjBcS
wBVNCtkASXFTu/aQUoHieVDIX/2IfpF38HbfejehiIDL3iywPQct/gSB4kkTmSt3
r/h0GGpUhMJoU42D0dMkQpk2p7sgtPusoaPEGCaTniccmjyvJcHHObCpQv+mCngZ
YwIDAQAB
-----END PUBLIC KEY-----
"""


def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: Session = Depends(get_db)
) -> models.User:
    """
    Dependency, яка перевіряє токен Clerk і повертає об'єкт користувача з MariaDB.
    Реалізує патерн Lazy Sync (створює юзера, якщо його ще немає в базі).
    """
    token = credentials.credentials

    try:
        # Валідуємо токен за допомогою публічного ключа Clerk
        # Алгоритм RS256 є стандартом для Clerk
        payload = jwt.decode(
            token,
            CLERK_PUBLIC_KEY,
            algorithms=["RS256"],
            options={"verify_aud": False}  # За потреби можна налаштувати валідацію audience
        )

        # 'sub' — це унікальний ID користувача в Clerk (наприклад, user_2bX...)
        clerk_id = payload.get("sub")
        if not clerk_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Токен не містить ідентифікатора користувача (sub)"
            )

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Термін дії токена закінчився")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Невалідний токен авторизації")

    # ЛОГІКА ІНТЕГРАЦІЇ З БД (Lazy Sync)
    # Шукаємо користувача в нашій MariaDB за його clerk_id
    user = db.query(models.User).filter(models.User.clerk_id == clerk_id).first()

    # Якщо користувач зайшов уперше і його ще немає в нашій БД
    if not user:
        user = models.User(clerk_id=clerk_id, xp=0)
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"Lazy Sync: Створено нового користувача {clerk_id} в MariaDB")

    return user
