import hashlib
import io
import os
import random
from typing import List

import uvicorn
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from google.cloud import texttospeech
from sqlalchemy.orm import Session, joinedload

import schemas
from achievement_manager import check_and_grant_achievements
from auth import get_current_user
from db import models
from db.database import engine, get_db
from poem_functions import get_poem_parts, prepare_poem_lines, extract_hidden_words
from utils import get_random_exercise_type

models.Base.metadata.create_all(bind=engine)

app = FastAPI()
client = texttospeech.TextToSpeechClient()

CACHE_DIR = "audio_cache"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

os.makedirs("uploads/images", exist_ok=True)

app.mount("/images", StaticFiles(directory="uploads/images"), name="images")

prompt: str = "Read aloud in a warm, welcoming tone."


@app.get("/generate-audio")
async def generate_audio(text: str = Query(...)):
    try:
        text_hash = hashlib.md5(text.encode()).hexdigest()
        file_path = os.path.join(CACHE_DIR, f"{text_hash}.mp3")

        if os.path.exists(file_path):
            print(f"--- Serving from cache: {text_hash}")
            return FileResponse(file_path, media_type="audio/mpeg")

        # print(text)
        print(f"--- Generating new audio via Google Cloud TTS...")
        synthesis_input = texttospeech.SynthesisInput(
            text=text,
            prompt=prompt
        )

        voice = texttospeech.VoiceSelectionParams(
            language_code="uk-UA",
            name="Achernar",
            model_name="gemini-3.1-flash-tts-preview"
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )

        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )

        with open(file_path, "wb") as out:
            out.write(response.audio_content)

        # Повертаємо бінарні дані як потік (без збереження у файл)
        return StreamingResponse(
            io.BytesIO(response.audio_content),
            media_type="audio/mpeg"
        )


    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 1. Отримання списку всіх віршів (з пагінацією)
@app.get("/poems", response_model=List[schemas.PoemWithAuthorResponse])
def get_poems(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    """
    Повертає список віршів.
    skip та limit використовуються для пагінації (щоб не вантажити всі 1000 віршів одразу).
    """
    poems = db.query(models.Poem).offset(skip).limit(limit).all()
    return poems


@app.get("/poems/studied", response_model=List[schemas.PoemWithAuthorResponse])
def get_studied_poems(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)  # Дістаємо поточного юзера
):
    """
    Повертає список унікальних віршів, для яких користувач має хоча б один результат тесту.
    Аналог: SELECT * FROM poems WHERE id IN (SELECT DISTINCT poem_id FROM test_results WHERE user_id = X);
    """

    # 1. Створюємо підзапит (Subquery) для отримання унікальних id віршів
    studied_poem_ids = (
        db.query(models.TestResult.poem_id)
        .filter(models.TestResult.user_id == current_user.id)
        .distinct()
        .subquery()
    )

    # 2. Робимо основний запит до таблиці poems, фільтруючи за підзапитом
    poems = db.query(models.Poem).filter(models.Poem.id.in_(studied_poem_ids)).all()

    return poems


# 2. Отримання конкретного вірша за ID
@app.get("/poems/{poem_id}", response_model=schemas.PoemWithAuthorResponse)
def get_poem(poem_id: int, db: Session = Depends(get_db)):
    """
    Повертає один вірш за його ID.
    """
    poem = db.query(models.Poem).filter(models.Poem.id == poem_id).first()

    if not poem:
        raise HTTPException(status_code=404, detail="Вірш не знайдено")

    return poem


# 3. Пошук віршів
@app.get("/search/poems", response_model=List[schemas.PoemWithAuthorResponse])
def search_poems(
        q: str = Query(..., min_length=2, description="Текст для пошуку"),
        db: Session = Depends(get_db)
):
    """
    Шукає вірші за назвою або частиною тексту.
    """
    # Додаємо % для SQL LIKE запиту (пошук входження рядка будь-де)
    search_query = f"%{q}%"

    # ilike забезпечує регістронезалежний пошук (неважливо, великі чи малі літери)
    poems = db.query(models.Poem).filter(
        (models.Poem.title.ilike(search_query)) |
        (models.Poem.text.ilike(search_query))
    ).all()

    return poems


@app.post("/tests/start")
def start_test(poem_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # Створюємо запис. start_time проставиться автоматично!

    print(f"Користувач з БД ID: {current_user.id}, Clerk ID: {current_user.clerk_id}")

    poem = db.query(models.Poem).filter(models.Poem.id == poem_id).first()
    if not poem:
        raise HTTPException(status_code=404, detail="Poem not found")

    text_parts = get_poem_parts(poem.text)
    #
    steps = []
    total_questions = 0
    for i, part in enumerate(text_parts):
        lines = prepare_poem_lines(part)
        hidden_words = extract_hidden_words(lines)
        random.shuffle(hidden_words)
        total_questions += len(hidden_words)
        steps.append({"step": i, "exercise_type": get_random_exercise_type(), "text": part, "lines": lines,
                      "hidden_words": hidden_words})

    new_test = models.TestResult(
        user_id=current_user.id,
        poem_id=poem_id,
        steps_count=len(text_parts),
        correct_count=0,
        total_count=total_questions
    )
    db.add(new_test)
    db.commit()
    db.refresh(new_test)

    return {
        "id": new_test.id,
        "user_id": new_test.user_id,
        "poem_id": new_test.poem_id,
        "steps_count": new_test.steps_count,
        "steps": steps,
    }


@app.post("/tests/{test_id}/finish")
def finish_test(
    test_id: int,
    correct_answers: int,
    tz: str = "Europe/Kyiv",
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    test_result = db.query(models.TestResult).filter(models.TestResult.id == test_id).first()
    if not test_result:
        raise HTTPException(status_code=404, detail="Test not found")

    # Перевірка безпеки: чи цей тест належить поточному юзеру
    if test_result.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    if test_result.finished == 1 or test_result.finished == True:
        raise HTTPException(status_code=400, detail=f"Test #{test_id} already finished")

    # current_user = db.query(models.User).filter(models.User.id == test_result.user_id).first()

    # Фіксуємо результати
    test_result.correct_count = correct_answers
    test_result.finished = True
    test_result.finish_test() # Твій автоматичний підрахунок секунд з першого питання!

    db.commit()
    db.refresh(test_result)

    # А ТЕПЕР МАГІЯ: Перевіряємо досягнення автоматично
    new_achievements = check_and_grant_achievements(current_user.id, db, tz)

    return {
        "message": "Test finished successfully",
        "time_spent": test_result.time_spent_seconds,
        # "current_xp": current_user.xp,
        "score": test_result.correct_count,
        "total_questions": test_result.total_count,
        # Якщо юзер щось відкрив, фронтенд отримає масив об'єктів і зможе показати красиве спокійне модальне вікно
        "new_achievements": [
            {"name": a.name, "description": a.description, "image": a.image}
            for a in new_achievements
        ]
    }


@app.post("/achievements", response_model=List[schemas.UserAchievementResponse])
def get_my_achievements(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)  # Автоматично дістаємо поточного юзера з Clerk
):
    """
    Повертає список усіх здобутих досягнень поточного автентифікованого користувача.
    Аналог: SELECT * FROM user_achievements JOIN achievements ON ... WHERE user_id = X;
    """
    achievements = (
        db.query(models.UserAchievement)
        .join(models.Achievement, models.UserAchievement.achievement_id == models.Achievement.id)
        .filter(models.UserAchievement.user_id == current_user.id)  # Використовуємо ID поточного юзера
        .options(joinedload(models.UserAchievement.achievement))  # Оптимізація: завантажуємо дані одним запитом
        .all()
    )

    return achievements


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

# Запуск локально: uvicorn main:app --reload
