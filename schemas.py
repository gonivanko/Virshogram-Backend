from pydantic import BaseModel
from typing import Optional


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


# class TestStep(BaseModel):
#     step: int
#     exercise_type: str
#     text: str
#     lines: list[str]
#
# class TestResponse(BaseModel):
#     id: int
#     user_id: int
#     poem_id: int
#     steps_count: int
