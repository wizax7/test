from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database import User, UserImages, UserVideos, UserGifs, UserDescriptions, UserAds
from utils import hashed_address

async def add_user_data(db: AsyncSession, user_data: dict):
    result = await db.execute(select(User).filter_by(user_id=user_data.get("user_id")))
    existing_user = result.scalars().first()
    user_id = user_data["user_id"]

    if existing_user is None:
        user = User(**user_data)
        db.add(user)
        user_images = UserImages(user_id=user_id)
        db.add(user_images)
        user_videos = UserVideos(user_id=user_id)
        db.add(user_videos)
        user_gifs = UserGifs(user_id=user_id)
        db.add(user_gifs)
        user_descriptions = UserDescriptions(user_id=user_id)
        db.add(user_descriptions)
        user_ads = UserAds(user_id=user_id)
        db.add(user_ads)
        await db.commit()
    else:
        print("Пользователь уже существует в базе данных.")

async def add_user_premium(db: AsyncSession, user_id: str):
    query = (
        update(User)
        .where(User.user_id == user_id)
        .values(is_premium_user=True)
    )

    await db.execute(query)
    await db.commit()

async def add_address(db: AsyncSession, user_id: str):
    query = (
        select(User.address)
        .filter_by(user_id=user_id)
    )
    result = await db.execute(query)
    existing_address = result.scalar_one_or_none()

    if existing_address is None:
        address = await hashed_address(user_id=user_id)
        
        query = (
            update(User)
            .where(User.user_id == user_id)
            .values(address=f"addr:{address}")
        )

        await db.execute(query)
        await db.commit()
    else:
        print("Адрес уже существует.")

async def read_all_users(db: AsyncSession):
    query = (select(User.user_id))

    result = await db.execute(query)
    result_rows = result.fetchall()
    
    user_ids = [user_id for row in result_rows for user_id in row]

    return user_ids

async def read_users_count(db: AsyncSession):
    query = (select(User.user_id))

    result = await db.execute(query)
    result_rows = result.fetchall()

    return len(result_rows)

async def read_username(db: AsyncSession, username: str):
    query = (
        select(User.user_name)
        .where(User.user_name == username)
    )

    result = await db.execute(query)
    user_name = result.scalar_one_or_none()

    return user_name

async def read_username_by_user_id(db: AsyncSession, user_id: str):
    stmt = (
        select(User.user_name)
        .where(User.user_id == user_id)
    )

    result = await db.execute(stmt)
    username = result.scalar_one_or_none()

    return username

async def get_id_by_username(db: AsyncSession, username: str):
    query = (
        select(User.user_id)
        .where(User.user_name == username)
    )

    result = await db.execute(query)
    user_id = result.scalar_one_or_none()

    return user_id

async def is_user_has_premium(db: AsyncSession, user_id: str):
    query = (
        select(User.is_premium_user)
        .where(User.user_id == user_id)
    )

    result = await db.execute(query)
    is_premium = result.scalar_one_or_none()

    return is_premium

async def read_user_language(db: AsyncSession, user_id: str):
    query = (
        select(User.language)
        .where(User.user_id == user_id)
    )

    result = await db.execute(query)
    language = result.scalar_one_or_none()

    return language

async def read_crystals_count(db: AsyncSession, user_id: str):
    query = (
        select(User.crystals)
        .where(User.user_id == user_id)
    )

    result = await db.execute(query)
    crystals_count = result.scalar_one_or_none()

    return crystals_count

async def read_address(db: AsyncSession, address: str):
    query = (
        select(User.address)
        .where(User.address == address)
    )    

    result = await db.execute(query)
    address = result.scalar_one_or_none()

    return address

async def read_address_by_user_id(db: AsyncSession, user_id: str):
    query = (
        select(User.address)
        .where(User.user_id == user_id)
    )

    result = await db.execute(query)
    address = result.scalar_one_or_none()

    return address

async def get_id_by_address(db: AsyncSession, address: str):
    query = (
        select(User.user_id)
        .where(User.address == address)
    )

    result = await db.execute(query)
    user_id = result.scalar_one_or_none()

    return user_id

async def update_username(db: AsyncSession, user_id: str, username: str):
    query = (
        update(User)
        .where(User.user_id == user_id)
        .values(user_name=username)
    )

    await db.execute(query)
    await db.commit()

async def update_language(db: AsyncSession, user_id: str, lang: str):
    query = (
        update(User)
        .where(User.user_id == user_id)
        .values(language=lang)
        .execution_options(synchronize_session="fetch")
    )

    await db.execute(query)
    await db.commit()


async def crediting_crystals(db: AsyncSession, user_id: str, crystals: float):
    query = (
        select(User.crystals)
        .where(User.user_id == user_id)
    )

    result = await db.execute(query)
    old_crystals_count = result.scalar_one_or_none()

    crystals_sum = old_crystals_count + crystals

    query = (
        update(User)
        .where(User.user_id == user_id)
        .values(crystals=crystals_sum)
        .execution_options(synchronize_session="fetch")
    )

    await db.execute(query)
    await db.commit()

async def crediting_crystals_to_user_by_username(db: AsyncSession, username: str, crystals: float):
    query = (
        select(User.crystals)
        .where(User.user_name == username)
    )

    result = await db.execute(query)
    old_crystals_count = result.scalar_one_or_none()

    crystals_sum = old_crystals_count + crystals

    query = (
        update(User)
        .where(User.user_name == username)
        .values(crystals=crystals_sum)
        .execution_options(synchronize_session="fetch")
    )

    await db.execute(query)
    await db.commit()

async def crediting_crystals_to_user_by_address(db: AsyncSession, address: str, crystals: float):
    query = (
        select(User.crystals)
        .where(User.address == address)
    )

    result = await db.execute(query)
    old_crystals_count = result.scalar_one_or_none()

    crystals_sum = old_crystals_count + crystals

    query = (
        update(User)
        .where(User.address == address)
        .values(crystals=crystals_sum)
        .execution_options(synchronize_session="fetch")
    )

    await db.execute(query)
    await db.commit()

async def crystals_substraction(db: AsyncSession, user_id: str, deductible_crystals: float):
    query = (
        select(User.crystals)
        .where(User.user_id == user_id)
    )
    
    result = await db.execute(query)
    old_crystals_count = result.scalar_one_or_none()
    
    new_crystals_count = old_crystals_count - deductible_crystals

    query = (
            update(User)
            .where(User.user_id == user_id)
            .values(crystals=new_crystals_count)
        )
    
    await db.execute(query)
    await db.commit()

async def delete_user(db: AsyncSession, user_id: str):
    user = await db.execute(select(User).where(User.user_id == user_id))
    user_data = user.scalars().first()

    await db.delete(user_data)
    await db.commit()

async def delete_user_premium(db: AsyncSession, user_id: str):
    query = (
        update(User)
        .where(User.user_id == user_id)
        .values(is_premium_user=False)
    )

    await db.execute(query)
    await db.commit()