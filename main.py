import hashlib
import io
import os
from typing import List

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session
from fastapi.staticfiles import StaticFiles
from google.cloud import texttospeech
from pydantic import BaseModel

import schemas
from poem_functions import get_poem_parts, prepare_poem_lines, extract_hidden_words
from utils import get_random_exercise_type

from db import models
from db.database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI()
client = texttospeech.TextToSpeechClient()

CACHE_DIR = "audio_cache"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

os.makedirs("uploads/images", exist_ok=True)

app.mount("/images", StaticFiles(directory="uploads/images"), name="images")

# POEMS_SERVICE_URL = "http://192.168.0.106:3000/poems"


prompt: str = "Read aloud in a warm, welcoming tone."


# 1. Модель для однієї відповіді (одного рядка)
class LineResult(BaseModel):
    hidden_token_index: int
    correct_word: str
    user_answer: str
    is_correct: bool


class TestResult(BaseModel):
    correct_count: int
    total_count: int


# # 2. Головна модель для всього тесту
# class TestSubmission(BaseModel):
#     poem_id: int
#     user_id: int  # Тимчасово передаємо так, пізніше візьмеш із токена авторизації
#     results: List[LineResult]
#     time_spent_seconds: int

# 2. Головна модель для всього тесту
class TestSubmission(BaseModel):
    poem_id: str
    user_id: str
    time_spent_seconds: int
    results: TestResult


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


@app.get("/test")
async def test(poem_id: str = Query(...), db: Session = Depends(get_db)):
    poem = db.query(models.Poem).filter(models.Poem.id == poem_id).first()
    if not poem:
        raise HTTPException(status_code=404, detail="Poem not found")

    text_parts = get_poem_parts(poem.text)
    #
    steps = []
    for i, part in enumerate(text_parts):
        lines = prepare_poem_lines(part)
        steps.append({"step": i, "exercise_type": get_random_exercise_type(), "text": part, "lines": lines,
                      "hidden_words": extract_hidden_words(lines)})

    print(steps)

    #
    # Повертаємо ці дані як відповідь нашого API
    return {
        "id": 1,
        "user_id": 1,
        "poem_id": poem_id,
        "steps_count": len(text_parts),
        "steps": steps,
    }


# 1. Отримання списку всіх віршів (з пагінацією)
@app.get("/poems", response_model=List[schemas.PoemWithAuthorResponse])
def get_poems(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    """
    Повертає список віршів.
    skip та limit використовуються для пагінації (щоб не вантажити всі 1000 віршів одразу).
    """
    poems = db.query(models.Poem).offset(skip).limit(limit).all()
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
def start_test(user_id: int, poem_id: int, db: Session = Depends(get_db)):
    # Створюємо запис. start_time проставиться автоматично!
    new_test = TestResult(
        user_id=user_id,
        poem_id=poem_id,
        steps_count=0,
        correct_count=0,
        total_count=10
    )
    db.add(new_test)
    db.commit()
    db.refresh(new_test)
    return {"test_id": new_test.id}


@app.post("/submit-test")
async def submit_test(submission: TestSubmission):
    try:
        # Рахуємо кількість правильних відповідей
        # correct_answers = sum(1 for item in submission.results if item.is_correct)
        # total_questions = len(submission.results)
        score = submission.results.correct_count / submission.results.total_count if submission.results.total_count > 0 else 0

        # print(f"--- Score: {score}")

        # TODO: Тут ти будеш зберігати дані в MariaDB
        # db.add(TestResult(user_id=..., poem_id=..., score=score))
        # db.commit()

        # Повертаємо фронтенду результати (наприклад, XP або нові досягнення)
        return {
            "status": "success",
            "score": score,
            "xp_earned": int(score * 100),
            "message": f"Тест завершено! {submission.results.correct_count} з {submission.results.total_count} правильно."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/users/{clerk_id}")
def get_user(clerk_id: str, db: Session = Depends(get_db)):
    # Звертаємось до бази через ORM
    user = db.query(models.User).filter(models.User.clerk_id == clerk_id).first()

    if not user:
        # Якщо юзера немає, створюємо його (Lazy Sync)
        new_user = models.User(clerk_id=clerk_id, xp=0)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user

    return user


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

# Запуск локально: uvicorn main:app --reload
