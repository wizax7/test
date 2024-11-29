import asyncio
import random

from sqlalchemy import Column, Integer, String, Boolean, Float, ForeignKey, select, update, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

from config import DB_URL
from utils import hashed_address

engine = create_async_engine(DB_URL)
async_session = sessionmaker(
    bind=engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    user_id = Column(String)
    full_name = Column(String)
    user_name = Column(String, nullable=True)
    
    is_premium_user = Column(Boolean, default=False)

    language = Column(String, default="ru")
    crystals = Column(Float, default=100)
    address = Column(String)

class UserImages(Base):
    __tablename__ = "user_photos"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.user_id"))
    image_id_ts = Column(String, nullable=True)
    image_id_cs = Column(String, nullable=True)


class UserVideos(Base):
    __tablename__ = "user_videos"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.user_id"))
    video_id_ts = Column(String, nullable=True)
    video_id_cs = Column(String, nullable=True)


class UserGifs(Base):
    __tablename__ = "user_gifs"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.user_id"))
    gif_id_ts = Column(String, nullable=True)
    gif_id_cs = Column(String, nullable=True)


class UserDescriptions(Base):
    __tablename__ = "user_descriptions"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.user_id"))
    description_ts = Column(String, nullable=True)
    description_cs = Column(String, nullable=True)

class UserAds(Base):
    __tablename__ = "user_ads"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.user_id"))
    is_ad_active_ts = Column(Boolean, default=False)
    is_ad_active_cs = Column(Boolean, default=False)
    creation_time_ad_ts = Column(String)
    creation_time_ad_cs = Column(String)
    key_word_ts = Column(String)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

#async def add_columns():
#    """Добавление новых столбцов в существующую таблицу."""
#    async with engine.connect() as connection:
#        try:
#            await connection.execute(text('ALTER TABLE user_ads ADD COLUMN creation_time_ad_ts TEXT;'))
#        except Exception as e:
#            print(f"Ошибка добавления creation_time_ad_ts: {e}")

#        try:
#            await connection.execute(text('ALTER TABLE user_ads ADD COLUMN creation_time_ad_cs TEXT;'))
#        except Exception as e:
#            print(f"Ошибка добавления creation_time_ad_cs: {e}")

#        try:
#            await connection.execute(text('ALTER TABLE user_ads ADD COLUMN key_word_ts TEXT;'))
#        except Exception as e:
#            print(f"Ошибка добавления key_word_ts: {e}")

#        print("Столбцы успешно добавлены.")

#async def main():
#    await init_db()
#    await add_columns()

#if __name__ == "__main__":
#    asyncio.run(main())