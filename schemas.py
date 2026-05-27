from datetime import datetime, timezone

from pydantic import BaseModel, field_serializer


# Базова схема для вірша
class PoemBase(BaseModel):
    title: str
    text: str
    author_id: int


# Схема для відповіді (додаємо id, який генерується в БД)
class PoemResponse(PoemBase):
    id: int

    class Config:
        # Цей конфіг дозволяє Pydantic читати дані безпосередньо з об'єктів SQLAlchemy
        from_attributes = True


# Схема для автора
class AuthorResponse(BaseModel):
    id: int
    name: str
    image: str

    class Config:
        from_attributes = True


class PoemWithAuthorResponse(PoemBase):
    id: int
    author: AuthorResponse  # Вкладаємо схему автора

    class Config:
        from_attributes = True

# Базова схема для самого досягнення (деталі)
class AchievementInfo(BaseModel):
    id: int
    name: str
    description: str
    xp_reward: int
    image: str

    class Config:
        from_attributes = True


class AchievementInfo(BaseModel):
    id: int
    name: str
    description: str
    xp_reward: int
    image: str

    class Config:
        from_attributes = True


# Основна схема відповіді
class UserAchievementResponse(BaseModel):
    id: int
    user_id: int
    achievement_id: int
    date_achieved: datetime  # Спочатку Pydantic зчитає її як naive
    achievement: AchievementInfo

    class Config:
        from_attributes = True

    @field_serializer('date_achieved')
    def serialize_datetime(self, dt: datetime, _info):
        """
        Кастомний серіалізатор: якщо дата прийшла з бази без часового поясу,
        ми примусово кажемо, що це UTC, і конвертуємо в ISO-рядок із символом 'Z'.
        """
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        # Повертає формат: 2026-05-26T07:12:51Z
        return dt.isoformat().replace("+00:00", "Z")
