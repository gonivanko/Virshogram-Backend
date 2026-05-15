import json
from database import SessionLocal, engine
import models


def seed_database():
    # 1. Створюємо таблиці, якщо їх ще немає
    models.Base.metadata.create_all(bind=engine)

    # Використовуємо ЄДИНУ сесію для всього процесу
    db = SessionLocal()

    try:
        # 2. Відкриваємо наш JSON файл
        with open('data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 3. Обробляємо авторів
        for author_data in data.get('authors', []):
            author = db.query(models.Author).filter_by(name=author_data["authorName"]).first()

            if not author:
                # Створюємо і ПРИСВОЮЄМО у змінну author
                author = models.Author(
                    name=author_data["authorName"],
                    image=author_data["authorImage"]
                )
                db.add(author)
                db.commit()
                db.refresh(author)  # Отримуємо author.id з бази
                print(f"Додано автора: {author.name}")

        # 4. Обробляємо вірші
        for poem_data in data.get('poems', []):
            existing_poem = db.query(models.Poem).filter_by(title=poem_data["title"]).first()

            if not existing_poem:
                author = db.query(models.Author).filter_by(name=poem_data["author"]).first()

                # Якщо автора раптом не було в блоці "authors", створюємо його тут
                if not author:
                    author = models.Author(
                        name=poem_data["author"],
                        image=poem_data.get("authorImage", "default.jpg")  # На випадок відсутності картинки
                    )
                    db.add(author)
                    db.commit()
                    db.refresh(author)
                    print(f"Додано нового автора з вірша: {author.name}")

                # Тепер змінна author 100% існує і має id
                poem = models.Poem(
                    author_id=author.id,
                    title=poem_data["title"],
                    text=poem_data["text"]
                )
                db.add(poem)
                print(f"Додано вірш: {poem.title}")

        db.commit()
        print("Базу даних успішно заповнено!")

    except Exception as e:
        db.rollback()  # Якщо щось зламається, база повернеться до початкового стану
        print(f"Помилка: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()