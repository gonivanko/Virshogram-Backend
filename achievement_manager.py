from sqlalchemy.orm import Session
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError  # <-- Імпортуємо для роботи з таймзонами
import db.models as models


def check_and_grant_achievements(user_id: int, db: Session, user_timezone_str: str = "Europe/Kyiv"):
    """
    Функція перевіряє історію користувача та нараховує нові досягнення
    з урахуванням часового поясу користувача.
    """
    # Валідація часового поясу (якщо прилетить некоректний рядок, дефолтимо на Київ)
    try:
        user_tz = ZoneInfo(user_timezone_str)
    except ZoneInfoNotFoundError:
        user_tz = ZoneInfo("Europe/Kyiv")

    # 1. Отримуємо ID всіх досягнень, які у юзера ВЖЕ Є
    existing_achievements = (
        db.query(models.UserAchievement.achievement_id)
        .filter(models.UserAchievement.user_id == user_id)
        .all()
    )
    existing_ids = {a[0] for a in existing_achievements}

    # 2. Витягуємо історію тестів користувача
    history = db.query(models.TestResult).filter(
        models.TestResult.user_id == user_id,
        models.TestResult.finished == True
    ).all()

    if not history:
        return []

    new_grants = []

    # --- УМОВА 1: "Глибоке занурення" ---
    ACH_DEEP_ID = 1
    if ACH_DEEP_ID not in existing_ids:
        for test in history:
            if test.steps_count > 0:
                avg_time_per_step = test.time_spent_seconds / test.steps_count
                if avg_time_per_step >= 25.0 and test.correct_count == test.total_count:
                    new_grants.append(ACH_DEEP_ID)
                    break

    # --- УМОВА 2: "Нічна поезія" (З урахуванням локального часу!) ---
    ACH_NIGHT_ID = 2
    if ACH_NIGHT_ID not in existing_ids:
        for test in history:
            if test.end_time:
                # Переконуємося, що об'єкт datetime знає, що він в UTC
                utc_time = test.end_time.replace(tzinfo=timezone.utc)

                # КОНВЕРТАЦІЯ: переводимо UTC у локальний час користувача
                local_time = utc_time.astimezone(user_tz)

                # Тепер беремо годину саме локального часу користувача
                local_hour = local_time.hour

                # print(utc_time, local_time, local_hour)

                if local_hour >= 22 or local_hour < 4:
                    new_grants.append(ACH_NIGHT_ID)
                    break

    # --- УМОВА 3: "Першовідкривач" ---
    ACH_FIRST_ID = 3
    if ACH_FIRST_ID not in existing_ids and len(history) >= 1:
        new_grants.append(ACH_FIRST_ID)

    # 3. Записуємо нові досягнення в базу даних
    granted_objects = []
    for ach_id in new_grants:
        user_ach = models.UserAchievement(
            user_id=user_id,
            achievement_id=ach_id,
            date_achieved=datetime.now(timezone.utc)
        )
        db.add(user_ach)

        ach_info = db.query(models.Achievement).filter(models.Achievement.id == ach_id).first()
        if ach_info:
            granted_objects.append(ach_info)
            user = db.query(models.User).filter(models.User.id == user_id).first()
            if user:
                user.xp += ach_info.xp_reward

    if new_grants:
        db.commit()

    return granted_objects