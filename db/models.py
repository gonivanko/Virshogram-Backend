from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, func
from sqlalchemy.orm import relationship

from db.database import Base
from datetime import datetime, timezone


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    clerk_id = Column(String(255), unique=True, index=True, nullable=False)
    xp = Column(Integer, default=0)


class Author(Base):
    __tablename__ = "authors"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    image = Column(String(255), nullable=False)

    poems = relationship("Poem", back_populates="author")


class Poem(Base):
    __tablename__ = "poems"

    id = Column(Integer, primary_key=True, index=True)
    author_id = Column(Integer, ForeignKey('authors.id'), nullable=False)
    title = Column(String(255), nullable=False)
    text = Column(Text, nullable=False)

    author = relationship("Author", back_populates="poems")


class Achievement(Base):
    __tablename__ = "achievements"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    xp_reward = Column(Integer, nullable=False)
    image = Column(String(255), nullable=False)


class UserAchievement(Base):
    __tablename__ = "user_achievements"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    achievement_id = Column(Integer, ForeignKey('achievements.id'), nullable=False)
    date_achieved = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now())


class TestResult(Base):
    __tablename__ = "test_results"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    poem_id = Column(Integer, ForeignKey('poems.id'), nullable=False)
    steps_count = Column(Integer, nullable=False)
    correct_count = Column(Integer, nullable=False)
    total_count = Column(Integer, nullable=False)
    finished = Column(Boolean, default=False, nullable=False)

    # Використовуємо Python-функцію для дефолтного часу створення
    start_time = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    time_spent_seconds = Column(Integer, nullable=True)

    def finish_test(self):
        """
        Метод, який викликається при завершенні тесту.
        Він автоматично ставить час завершення і рахує витрачені секунди.
        """
        # Фіксуємо час завершення
        self.end_time = datetime.now(timezone.utc)

        # Рахуємо різницю
        if self.start_time:
            delta = self.end_time - self.start_time
            self.time_spent_seconds = int(delta.total_seconds())
