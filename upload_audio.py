import os
import shutil

import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException

app = FastAPI()

# Створюємо папку для збереження файлів, якщо її немає
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/api/audio/upload")
async def upload_audio(audio: UploadFile = File(...)):
    try:
        # Перевіряємо, чи отримано файл
        if not audio.filename:
            raise HTTPException(status_code=400, detail="Файл не знайдено")

        # Формуємо шлях для збереження
        file_path = os.path.join(UPLOAD_DIR, audio.filename)

        # Зберігаємо файл локально
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(audio.file, buffer)

        print(f"Файл успішно збережено: {file_path}")

        return {
            "status": "success",
            "filename": audio.filename,
            "path": file_path,
            "message": "Аудіо успішно завантажено"
        }

    except Exception as e:
        print(f"Помилка збереження: {e}")
        raise HTTPException(status_code=500, detail=f"Помилка сервера: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)