from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Формат: mysql+драйвер://користувач:пароль@хост:порт/назва_бази
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://gonivanko:mariadb_ivan_23@127.0.0.1:3306/virshogram"

# Створюємо "двигун" підключення
engine = create_engine(SQLALCHEMY_DATABASE_URL, echo=True)
# echo=True означає, що в консолі ти будеш бачити всі SQL-запити (корисно для дебагу)

# Фабрика сесій (для створення тимчасових підключень на кожен запит)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Базовий клас, від якого ми будемо створювати наші таблиці (моделі)
Base = declarative_base()


# Функція (Dependency), яка буде видавати підключення кожному ендпоінту
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
