from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship

from db.database import Base


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


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
    test_results = relationship("TestResult", back_populates="poem")


class Achievement(Base):
    __tablename__ = "achievements"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    xp_reward = Column(Integer, nullable=False)
    image = Column(String(255), nullable=False)


class UserAchievement(Base):
    __tablename__ = "user_achievements"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    achievement_id = Column(Integer, ForeignKey('achievements.id'), nullable=False)
    date_achieved = Column(
        DateTime(timezone=False),
        nullable=False,
        default=utc_now
    )

    achievement = relationship("Achievement")


class TestResult(Base):
    __tablename__ = "test_results"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    poem_id = Column(Integer, ForeignKey('poems.id'), nullable=False)
    steps_count = Column(Integer, nullable=False)
    correct_count = Column(Integer, nullable=False)
    total_count = Column(Integer, nullable=False)
    finished = Column(Boolean, default=False, nullable=False)

    # Store UTC timestamps as timezone-naive values because MySQL/MariaDB
    # does not reliably preserve timezone information for DATETIME columns.
    start_time = Column(DateTime(timezone=False), default=utc_now, nullable=False)
    end_time = Column(DateTime(timezone=False), nullable=True)
    time_spent_seconds = Column(Integer, nullable=True)

    poem = relationship("Poem", back_populates="test_results")

    def finish_test(self):
        """
        Метод, який викликається при завершенні тесту.
        Він автоматично ставить час завершення і рахує витрачені секунди.
        """
        self.end_time = utc_now()
        self.finished = True

        if self.start_time:
            start_time = self.start_time

            if start_time.tzinfo is not None:
                start_time = start_time.astimezone(timezone.utc).replace(tzinfo=None)

            delta = self.end_time - start_time
            self.time_spent_seconds = max(0, int(delta.total_seconds()))
