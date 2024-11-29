import json
import re

from aiogram import Router, Bot, F 
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InputMediaPhoto
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiocryptopay import AioCryptoPay, Networks
from datetime import datetime

from config import CRYPTO_PAY_API_TOKEN
from database import async_session
from keyboards import CreateInlineButtons, CreateInlineButtonsWithLinks
from table_users import * 
from table_user_images import *
from table_user_videos import * 
from table_user_gifs import * 
from table_user_descs import * 
from table_users_ads import *
from utils import *

router = Router()
crypto_client = AioCryptoPay(token=CRYPTO_PAY_API_TOKEN, network=Networks.MAIN_NET)


'''
@router.message(Command("join_premium"))
async def join_premium(message: Message):
    user_id = message.from_user.id 

    async with async_session() as session:
        await add_user_premium(db=session, user_id=user_id)

    await message.answer("Вы успешно стали обладателем премиум подписки!")

@router.message(Command("quit_premium"))
async def quit_premium(message: Message):
    user_id = message.from_user.id 

    async with async_session() as session:
        await delete_user_premium(db=session, user_id=user_id)

    await message.answer("Премиум подписка отменена!")
'''
    

@router.message(Command("commands"))
async def commands(message: Message):
    user_id = message.from_user.id 
    user_data = {"user_id": message.from_user.id, "full_name": message.from_user.full_name, "user_name": message.from_user.full_name}
   
    async with async_session() as session:
        await add_user_data(db=session, user_data=user_data)
        await add_address(db=session, user_id=user_id)

    keyboard = CreateInlineButtons(count=6, text=["👥 Поиск команды", "⛩ Поиск клуба", "💎 Кристаллы", "⭐️ Премиум", "🌍 Язык", "⚙️ Настройки"], callback=["team_search", "club_search", "crystals", "premium", "language", "settings"], adjust=2).keyboard()
    await message.answer("💬 Выбери одну из команд:",
                         reply_markup=keyboard)
        
@router.callback_query(F.data == "back_to_commands")
async def back_to_commands(callback: CallbackQuery):
    keyboard = CreateInlineButtons(count=6, text=["👥 Поиск команды", "⛩ Поиск клуба", "💎 Кристаллы", "⭐️ Премиум", "🌍 Язык", "⚙️ Настройки"], callback=["team_search", "club_search", "crystals", "premium", "language", "settings"], adjust=2).keyboard()
    await callback.message.edit_text("💬 Выбери одну из команд:",
                         reply_markup=keyboard)


@router.callback_query(F.data == "team_search")
async def team_search(callback: CallbackQuery):
    user_id = callback.from_user.id 

    async with async_session() as session:
        is_premium = await is_user_has_premium(db=session, user_id=user_id)
        await add_user_in_users_ads(db=session, user_id=user_id)

    callback_options = ["show_ads_ts", "my_ad_ts"] if is_premium else ["search_ads_ts", "my_ad_ts"]
    keyboard = CreateInlineButtons(count=2, text=["🔎 Поиск", "📄 Мое объявление"], callback=callback_options, adjust=1).keyboard()
    await callback.message.edit_text("Выбери одну из кнопок:",
                                     reply_markup=keyboard)

@router.callback_query(F.data == "search_ads_ts")
async def search_ads_ts(callback: CallbackQuery):
    keyboard = CreateInlineButtons(count=1, text=["👌 Хорошо"], callback=["show_ads_ts"], adjust=1).keyboard()
    await callback.message.answer("💡 Совет: \nПопалось объявление нарушающие наши правила? Нажми на кнопку «⚠️ Репорт». Спасибо!",
                                  reply_markup=keyboard)
    
@router.callback_query(F.data.in_(["show_ads_ts", "continue_show_ads_ts", "continue_show_ads_ts2"]))
async def show_ads_ts(callback: CallbackQuery):
    user_id = f"{callback.from_user.id}"
    
    if user_id not in shown_ads_per_user:
        shown_ads_per_user[user_id] = set()

    async with async_session() as session:
        ad_info = await get_random_ads_ts(db=session, user_id=user_id, limit=1)

    if not ad_info:
        start_again_keyboard = CreateInlineButtons(count=2, text=["✅ Да", "❌ Нет"], callback=["continue_show_ads_ts2", "back_to_commands"], adjust=1).keyboard()
        await callback.message.answer("Все объявления были показаны. Начать заново?",
                                      reply_markup=start_again_keyboard
        )
        shown_ads_per_user[user_id].clear()  
        return

    ad = ad_info[0]
    media = next((ad[key] for key in ["image_id_ts", "video_id_ts", "gif_id_ts"] if ad.get(key)), None)
    ad_user_id = ad["user_id"]
    user_link = f"tg://user?id={ad_user_id}"

    shown_ads_per_user[user_id].add(ad_user_id)

    keyboard = CreateInlineButtonsWithLinks(count=3, text=["💬 Написать", "⚠️ Репорт", "➡️ Дальше"], url=[user_link, None, None], callback=[None, f"report_ts_{ad_user_id}", "continue_show_ads_ts"], adjust=1).keyboard()

    async with async_session() as session:
        creation_time = await read_creation_time_ts(db=session, user_id=ad_user_id)

    if creation_time:
        description = f"{ad['description_ts']} \n\n🗓️ {creation_time}"
        if ad["is_premium_user"]:
            description = f"{premium_labels[0]} \n\n{description} \n\n🗓️ {creation_time}"
    else: 
        description = f"{ad['description_ts']} \n\n🗓️ Дата еще не установлена"
        if ad["is_premium_user"]:
            description = f"{premium_labels[0]} \n\n{description} \n\n🗓️ Дата еще не установлена"

    if callback.data == "show_ads_ts":
        await callback.message.delete()

    if ad["image_id_ts"]:
        await callback.message.answer_photo(photo=media, caption=description, reply_markup=keyboard)
    elif ad["video_id_ts"]:
        await callback.message.answer_video(video=media, caption=description, reply_markup=keyboard)
    elif ad["gif_id_ts"]:
        await callback.message.answer_animation(animation=media, caption=description, reply_markup=keyboard)


@router.callback_query(F.data.startswith("report_ts_"))
async def report_ts(callback: CallbackQuery):
    reported_user_id = callback.data[10:]
    keyboard = CreateInlineButtons(count=2, text=["✅ Да", "⬅️ Назад"], callback=[f"final_report_ts_{reported_user_id}", "continue_show_ads_ts"], adjust=1).keyboard()
    await callback.message.answer("🤔 Вы уверены что хотите пожаловаться на этого пользователя? При ложных репортах вы можете быть наказаны. ⚖️",
                                  reply_markup=keyboard)
    
@router.callback_query(F.data.startswith("final_report_ts_"))
async def send_report_ts(callback: CallbackQuery, bot: Bot):
    caller_user_id = callback.from_user.id 
    owner_id = 1402290759
    reported_user_id = callback.data[16:]

    keyboard = CreateInlineButtons(count=1, text=["⬅️ Назад"], callback=[f"continue_show_ads_ts"], adjust=1).keyboard()
    await callback.message.edit_text("✅ Жалоба успешно отправлена!",
                                     reply_markup=keyboard)

    await bot.send_message(reported_user_id, f"⚠️ На ваше объявление в разделе «Поиск команды» поступил репорт. \nПожалуйста исправьте нарушение, если оно у вас есть. ❗️")
    await bot.send_message(owner_id, f"Пользователь с id `{caller_user_id}` пожаловался на объявление по поиску команды пользователя с id `{reported_user_id}`",
                                    parse_mode="MARKDOWN") 

@router.callback_query(F.data == "my_ad_ts")
async def my_ad_ts(callback: CallbackQuery):
    user_id = callback.from_user.id 

    async with async_session() as session:
        is_premium = await is_user_has_premium(db=session, user_id=user_id)
        is_ad_active = await read_status_ad_ts(db=session, user_id=user_id)
        is_cs_ad_active = await read_status_ad_cs(db=session, user_id=user_id)
        is_user_in_ban = await read_description_ts(db=session, user_id=user_id)

    if is_user_in_ban == "Забанен":
        keyboard = CreateInlineButtonsWithLinks(count=2, text=["💎 Купить разблокировку", "✉️ Наш канал"], callback=["buy_unban_ts", None], url=[None, "https://t.me/bs_searcher"], adjust=1).keyboard()
        await callback.message.edit_text("🔒 Вы заблокированы!",
                                         reply_markup=keyboard)
        return
    
    if is_ad_active == False and is_cs_ad_active == True and is_premium == False:
        keyboard = CreateInlineButtons(count=1, text=["⬅️ Назад"], callback=["back_to_commands"], adjust=1).keyboard()
        await callback.message.edit_text("📄 У вас уже есть активное объявление в разделе «Поиск клуба». \nПожалуйста скройте его, если хотите создать объявление в этом разделе. \n⭐️ Или приобретите подписку «Премиум» которая длится навсегда и открывает много возможностей.",
                                         reply_markup=keyboard)
        return

    if is_ad_active:
        keyboard = CreateInlineButtons(count=2, text=["✏️ Изменить", "👀 Скрыть"], callback=["edit_ad_ts", "delete_ad_ts"], adjust=1).keyboard() 
        await callback.message.edit_text("📄 У вас уже есть активное объявление, выберите действие:",
                                            reply_markup=keyboard)
        return 

    if is_premium:
        keyboard = CreateInlineButtons(count=2, text=["✅ Да", "⬅️ Назад"], callback=["edit_ad_ts", "back_to_commands"], adjust=1).keyboard()
        await callback.message.edit_text("📃 У вас нет объявления, хотите создать?",
                                              reply_markup=keyboard)
        return 

    keyboard = CreateInlineButtons(count=1, text=["👌 Ок"], callback=["read_rules_ts"], adjust=1).keyboard()
    await callback.message.edit_text("📌 Отлично! Но сперва ознакомься с нашими правилами.",
                                     reply_markup=keyboard) 
                                     
@router.callback_query(F.data == "read_rules_ts")
async def rules_ts(callback: CallbackQuery):
    keyboard = CreateInlineButtons(count=1, text=["✅ Я ознакомился"], callback=["edit_ad_ts"], adjust=1).keyboard()
    await callback.message.edit_text("<b>Реклама ❌ \n\nПосторонние ссылки ❌ \n\nНецензурная лексика ❌ \n\nКонтент 18+</b> ❌ \n\nПопалось объявление нарушающие наши правила? Нажмите на кнопку «⚠️ Репорт». Спасибо!",
                                     reply_markup=keyboard)

@router.callback_query(F.data.in_(["edit_ad_ts", "dont_add_media_ts"]))
async def creating_ad_ts(callback: CallbackQuery):
    user_id = callback.from_user.id 

    async with async_session() as session:
        image = await read_image_id_ts(db=session, user_id=user_id)
        video = await read_video_id_ts(db=session, user_id=user_id)
        gif = await read_gif_id_ts(db=session, user_id=user_id)


    if image:
        keyboard = CreateInlineButtons(count=3, text=["✅ Изображение", "🗑 Удалить", "👌 Готово"], callback=["media_ts", "delete_ts", "done_ts"], adjust=1).keyboard()
    elif video:
        keyboard = CreateInlineButtons(count=3, text=["✅ Видео", "🗑 Удалить", "👌 Готово"], callback=["media_ts", "delete_ts", "done_ts"], adjust=1).keyboard()
    elif gif:
        keyboard = CreateInlineButtons(count=3, text=["✅ GIF", "🗑 Удалить", "👌 Готово"], callback=["media_ts", "delete_ts", "done_ts"], adjust=1).keyboard()
    else:
        keyboard = CreateInlineButtons(count=1, text=["➕ Добавить медиа"], callback=["media_ts"], adjust=1).keyboard()

    if callback.data == "dont_add_media_ts":
        await callback.message.delete()
        await callback.message.answer("Выберите действие:",
                                      reply_markup=keyboard)
        return

    await callback.message.edit_text("Выберите действие:",
                                                reply_markup=keyboard)       


@router.callback_query(F.data == "media_ts")
async def choose_and_send_media_ts(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id 

    async with async_session() as session:
        is_premium_user = await is_user_has_premium(db=session, user_id=user_id)

    if is_premium_user:
        keyboard = CreateInlineButtons(count=3, text=["🖼 Изображение", "🎥 Видео", "🎞️ GIF"], callback=["get_image_ts", "get_video_ts", "get_gif_ts"], adjust=1).keyboard()
        await callback.message.edit_text("Выберите одну из медиа, которое будет в вашем объявлении:",
                                         reply_markup=keyboard)
        return 
    
    await state.set_state(TeamSearchStates.get_image)
    await callback.message.edit_text("🖼 Отправь изображение, которое будет отображаться в вашем объявлении:") 


@router.callback_query(F.data == "get_image_ts")
async def send_image_ts(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TeamSearchStates.get_image)

    await callback.message.edit_text("🖼 Отправь изображение, которое будет отображаться в вашем объявлении:")

@router.callback_query(F.data == "get_video_ts")
async def send_video_ts(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TeamSearchStates.get_video)

    await callback.message.edit_text("🎥 Отправь видео, которое будет отображаться в вашем объявлении:")

@router.callback_query(F.data == "get_gif_ts")
async def send_gif_ts(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TeamSearchStates.get_gif)

    await callback.message.edit_text("🎞️ Отправь GIF, которое будет отображаться в вашем объявлении:")


@router.message(TeamSearchStates.get_image)
async def get_image_ts(message: Message, state: FSMContext):
    try:
        image_id = message.photo[-1].file_id
        keyboard = CreateInlineButtons(count=2, text=["✅ Да", "❌ Нет"], callback=["set_image_ts", "dont_add_media_ts"], adjust=1).keyboard()

        await state.set_state(TeamSearchStates.set_image)
        await state.update_data(image_id=image_id)
        await message.answer_photo(photo=image_id, caption="Вы уверены что хотите добавить это изображение в ваше объявление?",
                                   reply_markup=keyboard)
    except Exception as e:
        keyboard = CreateInlineButtons(count=1, text=["⬅️ Назад"], callback=["dont_add_media_ts"], adjust=1).keyboard()
        await message.answer("Это не изображение!",
                             reply_markup=keyboard)
        print(e)
    
@router.message(TeamSearchStates.get_video)
async def get_video_ts(message: Message, state: FSMContext):
    try:
        video_id = message.video.file_id
        keyboard = CreateInlineButtons(count=2, text=["✅ Да", "❌ Нет"], callback=["set_video_ts", "dont_add_media_ts"], adjust=1).keyboard()

        await state.set_state(TeamSearchStates.set_video)
        await state.update_data(video_id=video_id)
        await message.answer_video(video=video_id, caption="Вы уверены что хотите добавить это видео в ваше объявление?",
                                   reply_markup=keyboard)
    except Exception as e:
        keyboard = CreateInlineButtons(count=1, text=["⬅️ Назад"], callback=["dont_add_media_ts"], adjust=1).keyboard()
        await message.answer("Это не видео!",
                             reply_markup=keyboard)
        print(e)

@router.message(TeamSearchStates.get_gif)
async def get_gif_ts(message: Message, state: FSMContext):
    try:
        gif_id = message.animation.file_id
        keyboard = CreateInlineButtons(count=2, text=["✅ Да", "❌ Нет"], callback=["set_gif_ts", "dont_add_media_ts"], adjust=1).keyboard()

        await state.set_state(TeamSearchStates.set_gif)
        await state.update_data(gif_id=gif_id)
        await message.answer_animation(animation=gif_id, caption="Вы уверены что хотите добавить эту GIF в ваше объявление?",
                                   reply_markup=keyboard)
    except Exception as e:
        keyboard = CreateInlineButtons(count=1, text=["⬅️ Назад"], callback=["dont_add_media_ts"], adjust=1).keyboard()
        await message.answer("Это не GIF!",
                             reply_markup=keyboard)
        print(e)

@router.callback_query(TeamSearchStates.set_image)
async def set_image_ts(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id 
    state_data = await state.get_data()
    image_id = state_data.get("image_id", 0)

    await state.clear()
    await callback.message.delete()

    async with async_session() as session:
        await add_image_ts(db=session, user_id=user_id, image_id=image_id)
        await delete_video_id_ts(db=session, user_id=user_id)
        await delete_gif_id_ts(db=session, user_id=user_id)

    keyboard = CreateInlineButtons(count=1, text=["⬅️ Назад"], callback=["edit_ad_ts"], adjust=1).keyboard()
    await callback.message.answer("✅ Изображение успешно установлено!",
                                     reply_markup=keyboard)


@router.callback_query(TeamSearchStates.set_video)
async def add_user_video_ts(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id 
    state_data = await state.get_data()
    video_id = state_data.get("video_id", 0)

    await state.clear()
    await callback.message.delete()

    async with async_session() as session:
        await add_video_ts(db=session, user_id=user_id, video_id=video_id)
        await delete_image_id_ts(db=session, user_id=user_id)
        await delete_gif_id_ts(db=session, user_id=user_id)

    keyboard = CreateInlineButtons(count=1, text=["⬅️ Назад"], callback=["edit_ad_ts"], adjust=1).keyboard()
    await callback.message.answer("✅ Видео успешно установлено!",
                                     reply_markup=keyboard)

@router.callback_query(TeamSearchStates.set_gif)
async def add_user_gif_ts(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id 
    state_data = await state.get_data()
    gif_id = state_data.get("gif_id", 0)

    await state.clear()
    await callback.message.delete()

    async with async_session() as session:
        await add_gif_ts(db=session, user_id=user_id, gif_id=gif_id)
        await delete_image_id_ts(db=session, user_id=user_id)
        await delete_video_id_ts(db=session, user_id=user_id)

    keyboard = CreateInlineButtons(count=1, text=["⬅️ Назад"], callback=["edit_ad_ts"], adjust=1).keyboard()
    await callback.message.answer("✅ GIF успешно установлен!",
                                     reply_markup=keyboard)

@router.callback_query(F.data == "delete_ts")
async def delete_media_ts(callback: CallbackQuery):
    user_id = callback.from_user.id 

    async with async_session() as session:
        image = await read_image_id_ts(db=session, user_id=user_id)
        video = await read_video_id_ts(db=session, user_id=user_id)
        gif = await read_gif_id_ts(db=session, user_id=user_id)

    await callback.message.delete()

    if image: 
        keyboard = CreateInlineButtons(count=2, text=["✅ Да", "❌ Нет"], callback=["delete_image_ts", "dont_add_media_ts"], adjust=1).keyboard()
        await callback.message.answer_photo(photo=image, caption="Вы уверены что хотите удалить изображение?",
                                            reply_markup=keyboard)
    elif video: 
        keyboard = CreateInlineButtons(count=2, text=["✅ Да", "❌ Нет"], callback=["delete_video_ts", "dont_add_media_ts"], adjust=1).keyboard()
        await callback.message.answer_video(video=video, caption="Вы уверены что хотите удалить видео?",
                                            reply_markup=keyboard)
    elif gif:
        keyboard = CreateInlineButtons(count=2, text=["✅ Да", "❌ Нет"], callback=["delete_gif_ts", "dont_add_media_ts"], adjust=1).keyboard()
        await callback.message.answer_animation(animation=gif, caption="Вы уверены что хотите удалить GIF?",
                                                reply_markup=keyboard)
    else:
        await callback.answer("🚫 У вас нет загруженных медиа!")
        
@router.callback_query(F.data.in_(["delete_image_ts", "delete_video_ts", "delete_gif_ts"]))
async def delete_media_ts_end(callback: CallbackQuery):
    user_id = callback.from_user.id 
    keyboard = CreateInlineButtons(count=1, text=["⬅️ Назад"], callback=["edit_ad_ts"], adjust=1).keyboard()

    await callback.message.delete()
            
    if callback.data == "delete_image_ts":
        async with async_session() as session:
            await delete_image_id_ts(db=session, user_id=user_id)
        await callback.message.answer("✅ Изображение успешно удалено!", 
                                      reply_markup=keyboard)
    if callback.data == "delete_video_ts":
        async with async_session() as session:
            await delete_video_id_ts(db=session, user_id=user_id)
        await callback.message.answer("✅ Видео успешно удалено!", 
                                      reply_markup=keyboard)
    if callback.data == "delete_gif_ts":
        async with async_session() as session:
            await delete_gif_id_ts(db=session, user_id=user_id)
        await callback.message.answer("✅ GIF успешно удален!", 
                                      reply_markup=keyboard)

@router.callback_query(F.data == "delete_ad_ts")
async def delete_ad_ts_start(callback: CallbackQuery):
    keyboard = CreateInlineButtons(count=2, text=["✅ Да", "⬅️ Назад"], callback=["sure_to_delete_ad_ts", "my_ad_ts"], adjust=1).keyboard()
    await callback.message.edit_text("👀 Вы уверены что хотите скрыть объявление? (Пользователи больше не смогут увидеть его, но все данные сохранятся)",
                                reply_markup=keyboard)

@router.callback_query(F.data == "sure_to_delete_ad_ts")
async def delete_ad_ts_end(callback: CallbackQuery):
    user_id = callback.from_user.id 

    async with async_session() as session:
        await delete_ad_in_active_ts(db=session, user_id=user_id)

    keyboard = CreateInlineButtons(count=1, text=["⬅️ Назад"], callback=["back_to_commands"], adjust=1).keyboard()
    await callback.message.edit_text("✅ Объявление успешно скрыто!",
                                  reply_markup=keyboard)

@router.callback_query(F.data == "done_ts")
async def done_ts(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id 

    async with async_session() as session:
        description = await read_description_ts(db=session, user_id=user_id)

    if description:
        keyboard = CreateInlineButtons(count=2, text=["✅ Да", "❌ Нет"], callback=["edit_description_ts", "post_exist_ad_ts"], adjust=1).keyboard()
        await callback.message.edit_text(f"🤔 У вас уже есть описание, хотите изменить его? \n<blockquote>{description}</blockquote>",
                                             reply_markup=keyboard)
        return

    await state.set_state(TeamSearchStates.get_description)
    await callback.message.edit_text("💭 Придумай описание:")

@router.callback_query(F.data == "edit_description_ts")
async def edit_description_ts(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TeamSearchStates.get_description)
    await callback.message.edit_text("💭 Придумай описание:")

@router.message(TeamSearchStates.get_description)
async def get_description(message: Message, state: FSMContext):
    description = message.text

    keyboard = CreateInlineButtons(count=1, text=["⬅️ Назад"], callback=["done_ts"], adjust=1).keyboard()
    keyboard2 = CreateInlineButtons(count=2, text=["✅ Да", "⬅️ Назад"], callback=["set_description", "done_ts"], adjust=1).keyboard()
    url_pattern = re.compile(r'http[s]?://\S+')
    mention_pattern = re.compile(r'@\w+')
    tme_pattern = re.compile(r't\.me/\w+')
    has_link = bool(url_pattern.search(description) or tme_pattern.search(description))
    has_mention = bool(mention_pattern.search(description))

    if len(description) < 20:
        await message.answer("🗯 Извини, но описание должно включать в себя не менее 20 символов",
                                reply_markup=keyboard)
        return
    if len(description) > 165: # было 120
        await message.answer("🗯 Извини, но описание должно включать в себя не более 165 символов",
                                reply_markup=keyboard)
        return
    if checking_bad_words(text=description):
        await message.answer("🗯 Описание содержит нецензурные или запрещенные слова. Пожалуйста, измените описание",
                                reply_markup=keyboard)
        return
    if has_link or has_mention:
        await message.answer("🗯 Описание не должно содержать ссылки или упоминания пользователей.",
                                reply_markup=keyboard)
        return
    
    await state.set_state(TeamSearchStates.set_description)
    await state.update_data(description=description)
    await message.answer(f"✅ Отлично! Ты точно хочешь применить это описание? \n<blockquote>{description}</blockquote>",
                            reply_markup=keyboard2)

@router.callback_query(TeamSearchStates.set_description)
async def set_desc_ts(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id 
    time = datetime.now().strftime("%d.%m.%Y")
    state_data = await state.get_data()
    description = state_data.get("description", 0) 
    #description_with_date = f"{description} \n\n{time}"

    await state.clear()
    async with async_session() as session:
        await add_creation_time_ts(db=session, user_id=user_id, time=time)
        await add_description_ts(db=session, user_id=user_id, description=description)

    keyboard = CreateInlineButtons(count=2, text=["👍 Да", "🔄 Вернуться в начало"], callback=["post_ad_ts", "my_ad_ts"], adjust=1).keyboard()
    await callback.message.edit_text("⁉️ Ну что, готов выложить свое объявление?",
                                        reply_markup=keyboard)

@router.callback_query(F.data == "post_exist_ad_ts")
async def post_exist_ad_ts(callback: CallbackQuery):
    user_id = callback.from_user.id 
    time = datetime.now().strftime("%d.%m.%Y")

    async with async_session() as session:
        await add_creation_time_ts(db=session, user_id=user_id, time=time)
        await add_ad_in_active_ts(db=session, user_id=user_id)
    
    keyboard = CreateInlineButtons(count=1, text=["⬅️ На главную"], callback=["back_to_commands"], adjust=1).keyboard()
    await callback.message.edit_text("🎉 Ваше объявление в списке активных! Удачи 🍀",
                                     reply_markup=keyboard)

@router.callback_query(F.data == "post_ad_ts")
async def post_ad_ts(callback: CallbackQuery):
    user_id = callback.from_user.id 
    async with async_session() as session:
        await add_ad_in_active_ts(db=session, user_id=user_id)
    
    keyboard = CreateInlineButtons(count=1, text=["⬅️ На главную"], callback=["back_to_commands"], adjust=1).keyboard()
    await callback.message.edit_text("🎉 Ваше объявление в списке активных! Удачи 🍀",
                                     reply_markup=keyboard)









# -------------------------------------------------------------------------------------------------------------------------------------------------------------------


@router.callback_query(F.data == "club_search")
async def club_search(callback: CallbackQuery):
    user_id = callback.from_user.id 

    async with async_session() as session:
        is_premium = await is_user_has_premium(db=session, user_id=user_id)
        await add_user_in_users_ads(db=session, user_id=user_id)

    callback_options = ["show_ads_cs", "my_ad_cs"] if is_premium else ["search_ads_cs", "my_ad_cs"]
    keyboard = CreateInlineButtons(count=2, text=["🔎 Поиск", "📄 Мое объявление"], callback=callback_options, adjust=1).keyboard()
    await callback.message.edit_text("Выбери одну из кнопок:",
                                     reply_markup=keyboard)

@router.callback_query(F.data == "search_ads_cs")
async def search_ads_cs(callback: CallbackQuery):
    keyboard = CreateInlineButtons(count=1, text=["👌 Хорошо"], callback=["show_ads_cs"], adjust=1).keyboard()
    await callback.message.answer("💡 Совет: \nПопалось объявление нарушающие наши правила? Нажми на кнопку «⚠️ Репорт». Спасибо!",
                                  reply_markup=keyboard)
    
@router.callback_query(F.data.in_(["show_ads_cs", "continue_show_ads_cs", "continue_show_ads_cs2"]))
async def show_ads_cs(callback: CallbackQuery):
    user_id = f"{callback.from_user.id}"
    
    if user_id not in shown_ads_per_user_cs:
        shown_ads_per_user_cs[user_id] = set()

    async with async_session() as session:
        ad_info = await get_random_ads_cs(db=session, user_id=user_id, limit=1)

    if not ad_info:
        start_again_keyboard = CreateInlineButtons(count=2, text=["✅ Да", "❌ Нет"], callback=["continue_show_ads_cs2", "back_to_commands"], adjust=1).keyboard()
        await callback.message.answer("Все объявления были показаны. Начать заново?",
                                      reply_markup=start_again_keyboard
        )
        shown_ads_per_user_cs[user_id].clear()  
        return

    ad = ad_info[0]
    media = next((ad[key] for key in ["image_id_cs", "video_id_cs", "gif_id_cs"] if ad.get(key)), None)
    ad_user_id = ad["user_id"]
    user_link = f"tg://user?id={ad_user_id}"

    shown_ads_per_user_cs[user_id].add(ad_user_id)

    keyboard = CreateInlineButtonsWithLinks(count=3, text=["💬 Написать", "⚠️ Репорт", "➡️ Дальше"], url=[user_link, None, None], callback=[None, f"report_cs_{ad_user_id}", "continue_show_ads_cs"], adjust=1).keyboard()

    async with async_session() as session:
        creation_time = await read_creation_time_cs(db=session, user_id=ad_user_id)

    if creation_time:
        description = f"{ad['description_cs']} \n\n🗓️ {creation_time}"
        if ad["is_premium_user"]:
            description = f"{premium_labels[0]} \n\n{description} \n\n🗓️ {creation_time}"
    else: 
        description = f"{ad['description_cs']} \n\n🗓️ Дата еще не установлена"
        if ad["is_premium_user"]:
            description = f"{premium_labels[0]} \n\n{description} \n\n🗓️ Дата еще не установлена"

    if callback.data == "show_ads_cs":
        await callback.message.delete()

    if ad["image_id_cs"]:
        await callback.message.answer_photo(photo=media, caption=description, reply_markup=keyboard)
    elif ad["video_id_cs"]:
        await callback.message.answer_video(video=media, caption=description, reply_markup=keyboard)
    elif ad["gif_id_cs"]:
        await callback.message.answer_animation(animation=media, caption=description, reply_markup=keyboard)


@router.callback_query(F.data.startswith("report_cs_"))
async def report_cs(callback: CallbackQuery):
    reported_user_id = callback.data[10:]
    keyboard = CreateInlineButtons(count=2, text=["✅ Да", "⬅️ Назад"], callback=[f"final_report_cs_{reported_user_id}", "continue_show_ads_cs"], adjust=1).keyboard()
    await callback.message.answer("🤔 Вы уверены что хотите пожаловаться на этого пользователя? При ложных репортах вы можете быть наказаны. ⚖️",
                                  reply_markup=keyboard)
    
@router.callback_query(F.data.startswith("final_report_cs_"))
async def send_report_cs(callback: CallbackQuery, bot: Bot):
    caller_user_id = callback.from_user.id 
    owner_id = 1402290759
    reported_user_id = callback.data[16:]

    keyboard = CreateInlineButtons(count=1, text=["⬅️ Назад"], callback=[f"continue_show_ads_cs"], adjust=1).keyboard()
    await callback.message.edit_text("✅ Жалоба успешно отправлена!",
                                     reply_markup=keyboard)

    await bot.send_message(reported_user_id, f"⚠️ На ваше объявление в разделе «Поиск клуба» поступил репорт. \nПожалуйста исправьте нарушение, если оно у вас есть. ❗️")
    await bot.send_message(owner_id, f"Пользователь с id `{caller_user_id}` пожаловался на объявление по поиску клуба пользователя с id `{reported_user_id}`",
                                    parse_mode="MARKDOWN") 

@router.callback_query(F.data == "my_ad_cs")
async def my_ad_cs(callback: CallbackQuery):
    user_id = callback.from_user.id 

    async with async_session() as session:
        is_premium = await is_user_has_premium(db=session, user_id=user_id)
        is_ad_active = await read_status_ad_cs(db=session, user_id=user_id)
        is_ts_ad_active = await read_status_ad_ts(db=session, user_id=user_id)
        is_user_in_ban = await read_description_cs(db=session, user_id=user_id)

    if is_user_in_ban == "Забанен":
        keyboard = CreateInlineButtonsWithLinks(count=2, text=["💎 Купить разблокировку", "✉️ Наш канал"], callback=["buy_unban_cs", None], url=[None, "https://t.me/bs_searcher"], adjust=1).keyboard()
        await callback.message.edit_text("🔒 Вы заблокированы!",
                                         reply_markup=keyboard)
        return

    if is_ad_active == False and is_ts_ad_active == True and is_premium == False:
        keyboard = CreateInlineButtons(count=1, text=["⬅️ Назад"], callback=["back_to_commands"], adjust=1).keyboard()
        await callback.message.edit_text("📄 У вас уже есть активное объявление в разделе «Поиск команды». \nПожалуйста скройте его, если хотите создать объявление в этом разделе. \n⭐️ Или приобретите подписку «Премиум» которая длится навсегда и открывает много возможностей.",
                                         reply_markup=keyboard)
        return

    if is_ad_active:
        keyboard = CreateInlineButtons(count=2, text=["✏️ Изменить", "👀 Скрыть"], callback=["edit_ad_cs", "delete_ad_cs"], adjust=1).keyboard() 
        await callback.message.edit_text("📄 У вас уже есть активное объявление, выберите действие:",
                                            reply_markup=keyboard)
        return 
    
    if is_premium:
        keyboard = CreateInlineButtons(count=2, text=["✅ Да", "⬅️ Назад"], callback=["edit_ad_cs", "back_to_commands"], adjust=1).keyboard()
        await callback.message.edit_text("📃 У вас нет объявления, хотите создать?",
                                              reply_markup=keyboard)
        return 
    
    keyboard = CreateInlineButtons(count=1, text=["👌 Ок"], callback=["read_rules_cs"], adjust=1).keyboard()
    await callback.message.edit_text("📌 Отлично! Но сперва ознакомься с нашими правилами.",
                                     reply_markup=keyboard) 


@router.callback_query(F.data == "read_rules_cs")
async def rules_ts(callback: CallbackQuery):
    keyboard = CreateInlineButtons(count=1, text=["✅ Я ознакомился"], callback=["edit_ad_cs"], adjust=1).keyboard()
    await callback.message.edit_text("<b>Реклама ❌ \n\nПосторонние ссылки ❌ \n\nНецензурная лексика ❌ \n\nКонтент 18+</b> ❌ \n\nПопалось объявление нарушающие наши правила? Нажмите на кнопку «⚠️ Репорт». Спасибо!",
                                     reply_markup=keyboard)

@router.callback_query(F.data.in_(["edit_ad_cs", "dont_add_media_cs"]))
async def creating_ad_cs(callback: CallbackQuery):
    user_id = callback.from_user.id 

    async with async_session() as session:
        image = await read_image_id_cs(db=session, user_id=user_id)
        video = await read_video_id_cs(db=session, user_id=user_id)
        gif = await read_gif_id_cs(db=session, user_id=user_id)


    if image:
        keyboard = CreateInlineButtons(count=3, text=["✅ Изображение", "🗑 Удалить", "👌 Готово"], callback=["media_cs", "delete_cs", "done_cs"], adjust=1).keyboard()
    elif video:
        keyboard = CreateInlineButtons(count=3, text=["✅ Видео", "🗑 Удалить", "👌 Готово"], callback=["media_cs", "delete_cs", "done_cs"], adjust=1).keyboard()
    elif gif:
        keyboard = CreateInlineButtons(count=3, text=["✅ GIF", "🗑 Удалить", "👌 Готово"], callback=["media_cs", "delete_cs", "done_cs"], adjust=1).keyboard()
    else:
        keyboard = CreateInlineButtons(count=1, text=["➕ Добавить медиа"], callback=["media_cs"], adjust=1).keyboard()

    if callback.data == "dont_add_media_cs":
        await callback.message.delete()
        await callback.message.answer("Выберите действие:",
                                      reply_markup=keyboard)
        return

    await callback.message.edit_text("Выберите действие:",
                                                reply_markup=keyboard)       


@router.callback_query(F.data == "media_cs")
async def choose_and_send_media_cs(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id 

    async with async_session() as session:
        is_premium_user = await is_user_has_premium(db=session, user_id=user_id)

    if is_premium_user:
        keyboard = CreateInlineButtons(count=3, text=["🖼 Изображение", "🎥 Видео", "🎞️ GIF"], callback=["get_image_cs", "get_video_cs", "get_gif_cs"], adjust=1).keyboard()
        await callback.message.edit_text("Выберите одну из медиа, которое будет в вашем объявлении:",
                                         reply_markup=keyboard)
        return 
    
    await state.set_state(ClubSearchStates.get_image)
    await callback.message.edit_text("🖼 Отправь изображение, которое будет отображаться в вашем объявлении:") 


@router.callback_query(F.data == "get_image_cs")
async def send_image_cs(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ClubSearchStates.get_image)

    await callback.message.edit_text("🖼 Отправь изображение, которое будет отображаться в вашем объявлении:")

@router.callback_query(F.data == "get_video_cs")
async def send_video_cs(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ClubSearchStates.get_video)

    await callback.message.edit_text("🎥 Отправь видео, которое будет отображаться в вашем объявлении:")

@router.callback_query(F.data == "get_gif_cs")
async def send_gif_cs(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ClubSearchStates.get_gif)

    await callback.message.edit_text("🎞️ Отправь GIF, которое будет отображаться в вашем объявлении:")


@router.message(ClubSearchStates.get_image)
async def get_image_cs(message: Message, state: FSMContext):
    try:
        image_id = message.photo[-1].file_id
        keyboard = CreateInlineButtons(count=2, text=["✅ Да", "❌ Нет"], callback=["set_image_cs", "dont_add_media_cs"], adjust=1).keyboard()

        await state.set_state(ClubSearchStates.set_image)
        await state.update_data(image_id=image_id)
        await message.answer_photo(photo=image_id, caption="Вы уверены что хотите добавить это изображение в ваше объявление?",
                                   reply_markup=keyboard)
    except Exception as e:
        keyboard = CreateInlineButtons(count=1, text=["⬅️ Назад"], callback=["dont_add_media_cs"], adjust=1).keyboard()
        await message.answer("Это не изображение!",
                             reply_markup=keyboard)
        print(e)
    
@router.message(ClubSearchStates.get_video)
async def get_video_cs(message: Message, state: FSMContext):
    try:
        video_id = message.video.file_id
        keyboard = CreateInlineButtons(count=2, text=["✅ Да", "❌ Нет"], callback=["set_video_cs", "dont_add_media_cs"], adjust=1).keyboard()

        await state.set_state(ClubSearchStates.set_video)
        await state.update_data(video_id=video_id)
        await message.answer_video(video=video_id, caption="Вы уверены что хотите добавить это видео в ваше объявление?",
                                   reply_markup=keyboard)
    except Exception as e:
        keyboard = CreateInlineButtons(count=1, text=["⬅️ Назад"], callback=["dont_add_media_cs"], adjust=1).keyboard()
        await message.answer("Это не видео!",
                             reply_markup=keyboard)
        print(e)

@router.message(ClubSearchStates.get_gif)
async def get_gif_cs(message: Message, state: FSMContext):
    try:
        gif_id = message.animation.file_id
        keyboard = CreateInlineButtons(count=2, text=["✅ Да", "❌ Нет"], callback=["set_gif_cs", "dont_add_media_cs"], adjust=1).keyboard()

        await state.set_state(ClubSearchStates.set_gif)
        await state.update_data(gif_id=gif_id)
        await message.answer_animation(animation=gif_id, caption="Вы уверены что хотите добавить эту GIF в ваше объявление?",
                                   reply_markup=keyboard)
    except Exception as e:
        keyboard = CreateInlineButtons(count=1, text=["⬅️ Назад"], callback=["dont_add_media_cs"], adjust=1).keyboard()
        await message.answer("Это не GIF!",
                             reply_markup=keyboard)
        print(e)

@router.callback_query(ClubSearchStates.set_image)
async def set_image_cs(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id 
    state_data = await state.get_data()
    image_id = state_data.get("image_id", 0)

    await state.clear()
    await callback.message.delete()

    async with async_session() as session:
        await add_image_cs(db=session, user_id=user_id, image_id=image_id)
        await delete_video_id_cs(db=session, user_id=user_id)
        await delete_gif_id_cs(db=session, user_id=user_id)

    keyboard = CreateInlineButtons(count=1, text=["⬅️ Назад"], callback=["edit_ad_cs"], adjust=1).keyboard()
    await callback.message.answer("✅ Изображение успешно установлено!",
                                     reply_markup=keyboard)


@router.callback_query(ClubSearchStates.set_video)
async def add_user_video_cs(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id 
    state_data = await state.get_data()
    video_id = state_data.get("video_id", 0)

    await state.clear()
    await callback.message.delete()

    async with async_session() as session:
        await add_video_cs(db=session, user_id=user_id, video_id=video_id)
        await delete_image_id_cs(db=session, user_id=user_id)
        await delete_gif_id_cs(db=session, user_id=user_id)

    keyboard = CreateInlineButtons(count=1, text=["⬅️ Назад"], callback=["edit_ad_cs"], adjust=1).keyboard()
    await callback.message.answer("✅ Видео успешно установлено!",
                                     reply_markup=keyboard)

@router.callback_query(ClubSearchStates.set_gif)
async def add_user_gif_cs(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id 
    state_data = await state.get_data()
    gif_id = state_data.get("gif_id", 0)

    await state.clear()
    await callback.message.delete()

    async with async_session() as session:
        await add_gif_cs(db=session, user_id=user_id, gif_id=gif_id)
        await delete_image_id_cs(db=session, user_id=user_id)
        await delete_video_id_cs(db=session, user_id=user_id)

    keyboard = CreateInlineButtons(count=1, text=["⬅️ Назад"], callback=["edit_ad_cs"], adjust=1).keyboard()
    await callback.message.answer("✅ GIF успешно установлен!",
                                     reply_markup=keyboard)

@router.callback_query(F.data == "delete_cs")
async def delete_media_cs(callback: CallbackQuery):
    user_id = callback.from_user.id 

    async with async_session() as session:
        image = await read_image_id_cs(db=session, user_id=user_id)
        video = await read_video_id_cs(db=session, user_id=user_id)
        gif = await read_gif_id_cs(db=session, user_id=user_id)

    await callback.message.delete()

    if image: 
        keyboard = CreateInlineButtons(count=2, text=["✅ Да", "❌ Нет"], callback=["delete_image_cs", "dont_add_media_cs"], adjust=1).keyboard()
        await callback.message.answer_photo(photo=image, caption="Вы уверены что хотите удалить изображение?",
                                            reply_markup=keyboard)
    elif video: 
        keyboard = CreateInlineButtons(count=2, text=["✅ Да", "❌ Нет"], callback=["delete_video_cs", "dont_add_media_cs"], adjust=1).keyboard()
        await callback.message.answer_video(video=video, caption="Вы уверены что хотите удалить видео?",
                                            reply_markup=keyboard)
    elif gif:
        keyboard = CreateInlineButtons(count=2, text=["✅ Да", "❌ Нет"], callback=["delete_gif_cs", "dont_add_media_cs"], adjust=1).keyboard()
        await callback.message.answer_animation(animation=gif, caption="Вы уверены что хотите удалить GIF?",
                                                reply_markup=keyboard)
    else:
        await callback.answer("🚫 У вас нет загруженных медиа!")
        
@router.callback_query(F.data.in_(["delete_image_cs", "delete_video_cs", "delete_gif_cs"]))
async def delete_media_cs_end(callback: CallbackQuery):
    user_id = callback.from_user.id 
    keyboard = CreateInlineButtons(count=1, text=["⬅️ Назад"], callback=["edit_ad_cs"], adjust=1).keyboard()

    await callback.message.delete()
            
    if callback.data == "delete_image_cs":
        async with async_session() as session:
            await delete_image_id_cs(db=session, user_id=user_id)
        await callback.message.answer("✅ Изображение успешно удалено!", 
                                      reply_markup=keyboard)
    if callback.data == "delete_video_cs":
        async with async_session() as session:
            await delete_video_id_cs(db=session, user_id=user_id)
        await callback.message.answer("✅ Видео успешно удалено!", 
                                      reply_markup=keyboard)
    if callback.data == "delete_gif_cs":
        async with async_session() as session:
            await delete_gif_id_cs(db=session, user_id=user_id)
        await callback.message.answer("✅ GIF успешно удален!", 
                                      reply_markup=keyboard)

@router.callback_query(F.data == "delete_ad_cs")
async def delete_ad_cs_start(callback: CallbackQuery):
    keyboard = CreateInlineButtons(count=2, text=["✅ Да", "⬅️ Назад"], callback=["sure_to_delete_ad_cs", "my_ad_cs"], adjust=1).keyboard()
    await callback.message.edit_text("👀 Вы уверены что хотите скрыть объявление? (Пользователи больше не смогут увидеть его, но все данные сохранятся)",
                                reply_markup=keyboard)

@router.callback_query(F.data == "sure_to_delete_ad_cs")
async def delete_ad_ts_end(callback: CallbackQuery):
    user_id = callback.from_user.id 

    async with async_session() as session:
        await delete_ad_in_active_cs(db=session, user_id=user_id)

    keyboard = CreateInlineButtons(count=1, text=["⬅️ Назад"], callback=["back_to_commands"], adjust=1).keyboard()
    await callback.message.edit_text("✅ Объявление успешно скрыто!",
                                  reply_markup=keyboard)

@router.callback_query(F.data == "done_cs")
async def done_cs(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id 

    async with async_session() as session:
        description = await read_description_cs(db=session, user_id=user_id)

    if description:
        keyboard = CreateInlineButtons(count=2, text=["✅ Да", "❌ Нет"], callback=["edit_description_cs", "post_exist_ad_cs"], adjust=1).keyboard()
        await callback.message.edit_text(f"🤔 У вас уже есть описание, хотите изменить его? \n<blockquote>{description}</blockquote>",
                                             reply_markup=keyboard)
        return

    await state.set_state(ClubSearchStates.get_description)
    await callback.message.edit_text("💭 Придумай описание:")

@router.callback_query(F.data == "edit_description_cs")
async def edit_description_cs(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ClubSearchStates.get_description)
    await callback.message.edit_text("💭 Придумай описание:")

@router.message(ClubSearchStates.get_description)
async def get_description_cs(message: Message, state: FSMContext):
    description = message.text

    keyboard = CreateInlineButtons(count=1, text=["⬅️ Назад"], callback=["done_cs"], adjust=1).keyboard()
    keyboard2 = CreateInlineButtons(count=2, text=["✅ Да", "⬅️ Назад"], callback=["set_description_cs", "done_cs"], adjust=1).keyboard()
    url_pattern = re.compile(r'http[s]?://\S+')
    mention_pattern = re.compile(r'@\w+')
    tme_pattern = re.compile(r't\.me/\w+')
    has_link = bool(url_pattern.search(description) or tme_pattern.search(description))
    has_mention = bool(mention_pattern.search(description))

    if len(description) < 20:
        await message.answer("🗯 Извини, но описание должно включать в себя не менее 20 символов",
                                reply_markup=keyboard)
        return
    if len(description) > 195: # было 120
        await message.answer("🗯 Извини, но описание должно включать в себя не более 195 символов",
                                reply_markup=keyboard)
        return
    if checking_bad_words(text=description):
        await message.answer("🗯 Описание содержит нецензурные или запрещенные слова. Пожалуйста, измените описание",
                                reply_markup=keyboard)
        return
    if has_link or has_mention:
        await message.answer("🗯 Описание не должно содержать ссылки или упоминания пользователей.",
                                reply_markup=keyboard)
        return
    
    await state.set_state(ClubSearchStates.set_description)
    await state.update_data(description=description)
    await message.answer(f"✅ Отлично! Ты точно хочешь применить это описание? \n<blockquote>{description}</blockquote>",
                            reply_markup=keyboard2)

@router.callback_query(ClubSearchStates.set_description)
async def set_desc_cs(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id 
    time = datetime.now().strftime("%d.%m.%Y")
    state_data = await state.get_data()
    description = state_data.get("description", 0)
    #description_with_date = f"{description} \n\n{time}"

    await state.clear()
    async with async_session() as session:
        await add_creation_time_cs(db=session, user_id=user_id, time=time)
        await add_description_cs(db=session, user_id=user_id, description=description)

    keyboard = CreateInlineButtons(count=2, text=["👍 Да", "🔄 Вернуться в начало"], callback=["post_ad_cs", "my_ad_cs"], adjust=1).keyboard()
    await callback.message.edit_text("⁉️ Ну что, готов выложить свое объявление?",
                                        reply_markup=keyboard)

@router.callback_query(F.data == "post_exist_ad_cs")
async def post_exist_ad_ts(callback: CallbackQuery):
    user_id = callback.from_user.id 
    time = datetime.now().strftime("%d.%m.%Y")

    async with async_session() as session:
        await add_creation_time_cs(db=session, user_id=user_id, time=time)
        await add_ad_in_active_cs(db=session, user_id=user_id)
    
    keyboard = CreateInlineButtons(count=1, text=["⬅️ На главную"], callback=["back_to_commands"], adjust=1).keyboard()
    await callback.message.edit_text("🎉 Ваше объявление в списке активных! Удачи 🍀",
                                     reply_markup=keyboard)

@router.callback_query(F.data == "post_ad_cs")
async def post_ad_cs(callback: CallbackQuery):
    user_id = callback.from_user.id 

    async with async_session() as session:
        await add_ad_in_active_cs(db=session, user_id=user_id)
    
    keyboard = CreateInlineButtons(count=1, text=["⬅️ На главную"], callback=["back_to_commands"], adjust=1).keyboard()
    await callback.message.edit_text("🎉 Ваше объявление в списке активных! Удачи 🍀",
                                     reply_markup=keyboard)




# -----------------------------------------------------------------------------------------




@router.callback_query(F.data == "crystals")
async def crystals(callback: CallbackQuery):
    user_id = callback.from_user.id 
    async with async_session() as session:
        crystals_count = await read_crystals_count(db=session, user_id=user_id)

    keyboard = CreateInlineButtons(count=3, text=["💳 Пополнить", "⬆️ Отправить", "⬇️ Получить"], callback=["top_up", "send", "receive"], adjust=1).keyboard()
    await callback.answer("⚠️ Внимание! Применений для кристаллов пока что нет")
    await callback.message.edit_text(f"На балансе {crystals_count} 💎 \nВыбери операцию:", 
                                    reply_markup=keyboard)

@router.callback_query(F.data == "top_up")
async def top_up(callback: CallbackQuery):
    await callback.answer("Пополнение баланса пока что недоступно.")

@router.callback_query(F.data == "send")
async def send(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SendCrystalsStates.chosen_way)
    keyboard = CreateInlineButtons(count=2, text=["По юзернейму", "По адресу"], callback=["by username", "by address"], adjust=1).keyboard()
    await callback.message.edit_text("🔑 Каким способом вы хотите отправить ваши кристаллы?", 
                                    reply_markup=keyboard)

@router.callback_query(SendCrystalsStates.chosen_way)
async def enter_username_or_address(callback: CallbackQuery, state: FSMContext):
    chosen_way = callback.data
    await state.set_state(SendCrystalsStates.enter_crystals_count)
    await state.update_data(chosen_way=chosen_way)

    if chosen_way == "by username":
        await callback.message.edit_text("Введи юзернейм получателя без @:")
    if chosen_way == "by address":
        await callback.message.edit_text("Введи адрес получателя:")

@router.message(SendCrystalsStates.enter_crystals_count)
async def enter_crystals_count(message: Message, state: FSMContext):
    user_id = message.from_user.id 
    state_data = await state.get_data()
    chosen_way = state_data.get("chosen_way", 0)

    async with async_session() as session:
        crystals_count = await read_crystals_count(db=session, user_id=user_id)

    if chosen_way == "by username":
        entered_username = message.text 
        async with async_session() as session:
            username = await read_username(db=session, username=entered_username)
        if username:
            await state.update_data(username=username)

            if crystals_count <= 0:
                await message.answer(f"Операция недоступна! \nНа вашем балансе {crystals_count} 💎")
            else:
                await state.set_state(SendCrystalsStates.confirmation)
                await message.answer(f"На балансе {crystals_count} 💎 \nВведи кол-во отправляемых кристаллов на юзернейм @{username}:")
        else:
            await message.answer("Пользователь не найден!")
    
    if chosen_way == "by address":
        entered_address = message.text 
        async with async_session() as session:
            address = await read_address(db=session, address=entered_address)
        if address:
            await state.update_data(address=address)
            if crystals_count <= 0:
                await message.answer(f"Операция недоступна! \nНа вашем балансе {crystals_count} 💎")
            else:
                await state.set_state(SendCrystalsStates.confirmation)
                await message.answer(f"На балансе {crystals_count} 💎 \nВведи кол-во отправляемых кристаллов на адрес: \n`{address}`",
                                        parse_mode="MARKDOWN")
        else: 
            await message.answer("Адрес не найден!")



@router.message(SendCrystalsStates.confirmation)
async def send_confirmation(message: Message, state: FSMContext):
    try:
        user_id = message.from_user.id 
        crystals_being_sent = float(message.text)
        state_data = await state.get_data()
        chosen_way = state_data.get("chosen_way", 0)
        await state.update_data(crystals=crystals_being_sent)

        async with async_session() as session:
            current_crystals_count = await read_crystals_count(db=session, user_id=user_id)

        if chosen_way == "by username":
            username = state_data.get("username", 0)
            username_or_address = f"Юзернейм: @{username}"
        if chosen_way == "by address":
            address = state_data.get("address", 0)
            username_or_address = f"Адрес: \n`{address}`"

        if crystals_being_sent <= 0:
            keyboard = CreateInlineButtons(count=1, text=["⬅️ Назад"], callback=["back_to_commands"], adjust=1).keyboard()
            await message.answer("Операция недоступна! Для отправки необходимо не менее 1 кристалла.",
                                 reply_markup=keyboard)
        else:
            keyboard = CreateInlineButtons(count=1, text=["⬆️ Отправить"], callback=["confirm sending"], adjust=1).keyboard()
            await state.set_state(SendCrystalsStates.opperation_end)
            await message.answer(f"Отправляемое кол-во кристаллов: {crystals_being_sent} 💎 \nБаланс: {current_crystals_count} 💎 \n{username_or_address}", 
                                    reply_markup=keyboard, parse_mode="MARKDOWN")
    except Exception as e:
        print(e)
        keyboard = CreateInlineButtons(count=1, text=["⬅️ Назад"], callback=["back_to_commands"], adjust=1).keyboard()
        await message.answer("Неверный тип данных!",
                             reply_markup=keyboard)

@router.callback_query(SendCrystalsStates.opperation_end)
async def opperartion_end(callback: CallbackQuery, state: FSMContext, bot: Bot):
    user_id = callback.from_user.id 
    caller_username = callback.from_user.username
    state_data = await state.get_data()
    chosen_way = state_data.get("chosen_way", 0)
    address = state_data.get("address", 0)
    crystals = state_data.get("crystals", 0)

    async with async_session() as session: 
        await crystals_substraction(db=session, user_id=user_id, deductible_crystals=crystals)
        balance = await read_crystals_count(db=session, user_id=user_id)

    if chosen_way == "by username":
        username = state_data.get("username", 0)
        async with async_session() as session:
            await crediting_crystals_to_user_by_username(db=session, username=username, crystals=crystals)
            recipient_id = await get_id_by_username(db=session, username=username)
            recipient_lang = await read_user_language(db=session, user_id=recipient_id)

        if caller_username:
            await bot.send_message(recipient_id, f"Пользователь @{caller_username} начислил вам {crystals} 💎")
        else:
            await bot.send_message(recipient_id, f"Неизвестный пользователь начислил вам {crystals} 💎")

    if chosen_way == "by address":
        address = state_data.get("address", 0)
        async with async_session() as session:
            await crediting_crystals_to_user_by_address(db=session, address=address, crystals=crystals)
            recipient_id = await get_id_by_address(db=session, address=address)
            recipient_lang = await read_user_language(db=session, user_id=recipient_id)

        await callback.message.edit_text(f"{crystals} 💎 были успешно отправлены по адресу: \n`{address}` \nТекущий баланс: {balance} 💎",
                                            parse_mode="MARKDOWN")

        if caller_username:
            await bot.send_message(recipient_id, f"Пользователь @{caller_username} начислил вам {crystals} 💎")
        else:
            await bot.send_message(recipient_id, f"Неизвестный пользователь начислил вам {crystals} 💎")

    await state.clear()


@router.callback_query(F.data == "receive")
async def receive(callback: CallbackQuery):
    user_id = callback.from_user.id 
    username = callback.from_user.username

    async with async_session() as session:
        address = await read_address_by_user_id(db=session, user_id=user_id)


    if username is None: 
        await callback.message.edit_text(f"Ваш адрес: \n`{address}`",
                                            parse_mode="MARKDOWN")
    else: 
        await callback.message.edit_text(f"Ваш адрес: \n`{address}` \n\nВаш юзернейм: @{username}",
                                            parse_mode="MARKDOWN")


@router.callback_query(F.data == "premium")
async def premium(callback: CallbackQuery):
    user_id = callback.from_user.id 

    async with async_session() as session:
        is_premium = await is_user_has_premium(db=session, user_id=user_id)

    if is_premium:
        keyboard = CreateInlineButtons(count=1, text=["⬅️ На главную"], callback=["back_to_commands"], adjust=1).keyboard()
        await callback.message.edit_text("⭐️ У вас уже есть премиум подписка. Наслаждайтесь ей по полной! 🍭",
                                         reply_markup=keyboard)
        return 
    keyboard = CreateInlineButtons(count=3, text=["🛒 Купить", "📊 Что я получу?", "⬅️ На главную"], callback=["buy_premium", "premium_benefits", "back_to_commands"], adjust=1).keyboard()
    await callback.message.edit_text("🍭 Насладитесь по полной всеми возможностями бота с премиум подпиской!",
                                     reply_markup=keyboard)

@router.callback_query(F.data == "buy_premium")
async def buy_premium(callback: CallbackQuery):
    try:
        invoice = await crypto_client.create_invoice(asset="USDT", amount=2.5)
        invoice_url = invoice.bot_invoice_url    
        invoice_id = invoice.invoice_id

        keyboard = CreateInlineButtonsWithLinks(count=2, text=["💸 Оплатить 2.5 USDT", "✅ Проверить оплату"], callback=[None, f"check_{invoice_id}"], url=[invoice_url, None], adjust=1).keyboard()
        old_photo = "AgACAgIAAxkBAAIHNGc-QnzUWz-muXcn-AjjmXB2bR9RAAJq6TEbqHvxSdVSzQitiBQzAQADAgADeAADNgQ"
        await callback.message.delete()
        new_photo = "AgACAgIAAxkBAAIfP2dHCPiEYu8_sK2XPat5UYks5YNMAAKh8TEbyR4xSgf-RMIznEVlAQADAgADeQADNgQ"
        await callback.message.answer_photo(photo=new_photo,
                                            caption="Ваш чек на оплату 2.5 USDT готов. Нажмите кнопку ниже, чтобы оплатить:", reply_markup=keyboard)
        #await callback.message.answer("Ваш чек на оплату 2.5 USDT готов. Нажмите кнопку ниже, чтобы оплатить:", reply_markup=keyboard)

    except Exception as e:
        print(e)
        keyboard = CreateInlineButtons(count=1, text=["⬅️ На главную"], callback=["back_to_commands"], adjust=1).keyboard()
        await callback.message.answer("⚠️ Ошибка при создании чека!",
                                         reply_markup=keyboard)

@router.callback_query(F.data.startswith("check_"))
async def check_invoice(callback: CallbackQuery):
    user_id = callback.from_user.id
    invoice_id = callback.data[6:]

    try:
        invoices = await crypto_client.get_invoices(invoice_ids=invoice_id)
        for invoice in invoices:
            if invoice.status == "paid":
                async with async_session() as session:
                    await add_user_premium(db=session, user_id=user_id)
                await callback.message.delete()
                await callback.message.answer("🎉 Оплата прошла успешно! Теперь у вас есть премиум подписка ⭐️")
            else:
                await callback.message.answer("Оплатите счет!")
    except Exception as e:
        await callback.message.answer(f"⚠️ Ошибка при проверке оплаты! Попробуйте обратиться в поддержку.")

@router.callback_query(F.data == "premium_benefits")
async def premium_benefits(callback: CallbackQuery):
    keyboard = CreateInlineButtons(count=2, text=["🛒 Купить", "⬅️ На главную"], callback=["buy_premium", "back_to_commands"], adjust=1).keyboard()
    await callback.message.edit_text(premium_benefits_var,
                                     reply_markup=keyboard)

@router.callback_query(F.data == "language")
async def language(callback: CallbackQuery):
    await callback.answer("🔜 Скоро...")


@router.callback_query(F.data == "settings")
async def settings(callback: CallbackQuery):
    keyboard = CreateInlineButtons(count=8, text=["🔗 Поделиться ботом", "🔢 Кол-во объявлений", "🔜 Скоро", "🔜 Скоро", "🔜 Скоро", "🔜 Скоро", "🔜 Скоро", "🔜 Скоро"], callback=["share_bot", "ads_count", "soon", "soon", "soon", "soon", "soon", "soon"], adjust=2).keyboard()
    await callback.message.edit_text("Выбери одно из действий:",
                                     reply_markup=keyboard)

@router.callback_query(F.data == "share_bot")
async def share_bot(callback: CallbackQuery):
    photo = "AgACAgIAAxkBAAIfRWdHCdzf9FHysugduHXwVxJHKljzAAKg8TEbyR4xSjGXUpPDBTtdAQADAgADeQADNgQ"
    await callback.message.delete()
    await callback.message.answer_photo(photo=photo, caption="Привет! 🎉 Нашёл место, где можно найти тиммейтов, друзей и даже целые клубы! 🎯 Присоединяйся и становись частью чего-то большего! 😉")
    await callback.message.answer("P.S Перешли это сообщение своим друзьям, знакомым и тем кому может быть это полезно. Спасибо! 💖")

@router.callback_query(F.data == "ads_count")
async def call_ads_count(callback: CallbackQuery, state: FSMContext):
    #await callback.answer("Скоро...")
    await state.set_state(GetAdsCount.get_count)
    keyboard = CreateInlineButtons(count=2, text=["👥 Поиск команды", "⛩ Поиск клуба"], callback=["view_ads_count_ts", "view_ads_count_cs"], adjust=1).keyboard()
    await callback.message.edit_text("В каком разделе тебя интересует количество активных объявлений?",
                                     reply_markup=keyboard)
    
    
@router.callback_query(GetAdsCount.get_count)
async def send_ads_count_cs(callback: CallbackQuery):
    where = callback.data
    keyboard = CreateInlineButtons(count=1, text=["⬅️ Назад"], callback=["ads_count"], adjust=1).keyboard()

    async with async_session() as session:
        ts_ads_count = await read_ads_count_ts(db=session)
        cs_ads_count = await read_ads_count_cs(db=session)

    if where == "view_ads_count_ts":
        await callback.message.edit_text(f"🕒 На данный момент в разделе «Поиск команды» насчитывается <b>{ts_ads_count}</b> активных объявлений. 📄",
                                        reply_markup=keyboard)
        return

    if where == "view_ads_count_cs":
        await callback.message.edit_text(f"🕒 На данный момент в разделе «Поиск клуба» насчитывается <b>{cs_ads_count}</b> активных объявлений. 📄",
                                            reply_markup=keyboard)
        return

@router.callback_query(F.data == "soon")
async def soon(callback: CallbackQuery):
    await callback.answer("Скоро...")

@router.message(Command("admin_panel"))
async def admin_panel(message: Message):
    user_id = message.from_user.id 

    if str(user_id) == "1402290759":
        keyboard = CreateInlineButtons(count=6, text=["🔢 Кол-во пользователей", "🔊 Рассылка", "Скрыть объявление", "Заблокировать пользователя", "Разблокировать объявление", "Объявление по user_id"], callback=["users count", "broadcast", "hide_ad_admin", "ban_user_admin", "unban_user_admin", "get_ad_by_user_id"], adjust=2).keyboard()
        await message.answer("Добро пожаловать в админ панель! Выбери одну из опций:", 
                                reply_markup=keyboard)
    else:
        await message.answer("Недоступно!")

@router.callback_query(F.data == "users count")
async def show_users_count(callback: CallbackQuery): 
    async with async_session() as session:
        users_count = await read_users_count(db=session)

    time = datetime.now().strftime("%H:%M %d.%m.%Y")
    await callback.message.edit_text(f"На момент {time}, количество пользователей бота достигает {users_count}!")


@router.callback_query(F.data == "broadcast")
async def broadcast(callback: CallbackQuery):
    keyboard = CreateInlineButtons(count=4, text=["📝 Текст", "🖼 Фото", "📹 Видео", "✉️ Гиф"], callback=["text broadcast", "photo broadcast", "video broadcast", "gif broadcast"], adjust=2).keyboard()
    await callback.message.edit_text("💬 Выбери тип рассылки:",
                        reply_markup=keyboard)

@router.callback_query(F.data == "text broadcast")
async def text_broadcast_enter(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Broadcast.start_text_broadcast)
    await callback.message.delete()
    await callback.message.edit_text("Введи текст:")

@router.message(Broadcast.start_text_broadcast)
async def start_text_broadcast(message: Message, state: FSMContext, bot: Bot):
    text = message.text
    await state.clear()
    async with async_session() as session:
        users_id = await read_all_users(db=session)
        await broadcast_message_only_text(message=text, users=users_id, bot=bot)
    await message.answer("Рассылка успешно завершена.")

@router.callback_query(F.data == "photo broadcast")
async def photo_broadcast_enter(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Broadcast.start_photo_broadcast)
    await callback.message.delete()
    await callback.message.answer("Отправь фото с описанием:")

@router.message(Broadcast.start_photo_broadcast)
async def start_photo_broadcast(message: Message, state: FSMContext, bot: Bot):
    photo_id = message.photo[-1].file_id
    caption = message.caption
    await state.clear()
    async with async_session() as session:
        users_id = await read_all_users(db=session)
        await broadcast_message_with_photo(photo_id=photo_id, caption=caption, users=users_id, bot=bot)
    await message.answer("Рассылка успешно завершена.")

@router.callback_query(F.data == "video broadcast")
async def video_broadcast_enter(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Broadcast.start_video_broadcast)
    await callback.message.delete()
    await callback.message.answer("Отправь видео с описанием:")

@router.message(Broadcast.start_video_broadcast)
async def start_video_broadcast(message: Message, state: FSMContext, bot: Bot):
    video_id = message.video.file_id
    caption = message.caption
    await state.clear()
    async with async_session() as session:
        users_id = await read_all_users(db=session)
        await broadcast_message_with_video(video_id=video_id, caption=caption, users=users_id, bot=bot)
    await message.answer("Рассылка успешно завершена.")

@router.callback_query(F.data == "gif broadcast")
async def gif_broadcast_enter(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Broadcast.start_gif_broadcast)
    await callback.message.delete()
    await callback.message.answer("Отправь гиф с описанием:")

@router.message(Broadcast.start_gif_broadcast)
async def start_video_broadcast(message: Message, state: FSMContext, bot: Bot):
    gif_id = message.animation.file_id
    caption = message.caption
    await state.clear()
    async with async_session() as session:
        users_id = await read_all_users(db=session)
        await broadcast_message_with_gif(gif_id=gif_id, caption=caption, users=users_id, bot=bot)
    await message.answer("Рассылка успешно завершена.")

@router.callback_query(F.data == "hide_ad_admin")
async def hide_ad(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminPanel.get_user_id_hide_ad)

    await callback.message.edit_text("Введите id пользователя:")


@router.message(AdminPanel.get_user_id_hide_ad)
async def get_user_id_hide_ad(message: Message, state: FSMContext):
    user_id = message.text
    keyboard = CreateInlineButtons(count=2, text=["Поиск команды", "Поиск клуба"], callback=[f"admin_hide_ad_ts_{user_id}", f"admin_hide_ad_cs_{user_id}"], adjust=1).keyboard()
    await state.clear()
    await message.answer("Где находится объявление нарушителя?",
                                     reply_markup=keyboard)

@router.callback_query(F.data.startswith("admin_hide_ad_ts_"))
async def admin_hide_ad_ts(callback: CallbackQuery, bot: Bot):
    user_id = callback.data[17:]
    async with async_session() as session:
            await delete_ad_in_active_ts(db=session, user_id=user_id)

    await bot.send_message(user_id, "⚠️ Ваше объявление в разделе «Поиск команды» было снято модератором. \nПожалуйста исправьте нарушение!")
    await callback.message.answer("✅ Объявление успешно снято.")

@router.callback_query(F.data.startswith("admin_hide_ad_cs_"))
async def admin_hide_ad_cs(callback: CallbackQuery, bot: Bot):
    user_id = callback.data[17:]
    async with async_session() as session:
            await delete_ad_in_active_cs(db=session, user_id=user_id)

    await bot.send_message(user_id, "⚠️ Ваше объявление в разделе «Поиск клуба» было снято модератором. \nПожалуйста исправьте нарушение!")
    await callback.message.answer("✅ Объявление успешно снято.")

@router.callback_query(F.data == "ban_user_admin")
async def ban_user(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminPanel.get_user_id_ban)

    await callback.message.edit_text("Введите id пользователя:")

@router.message(AdminPanel.get_user_id_ban)
async def get_user_id_ban_ad(message: Message, state: FSMContext):
    user_id = message.text
    keyboard = CreateInlineButtons(count=2, text=["Поиск команды", "Поиск клуба"], callback=[f"admin_ban_ad_ts_{user_id}", f"admin_ban_ad_cs_{user_id}"], adjust=1).keyboard()
    await state.clear()
    await message.answer("Где находится объявление нарушителя?",
                                     reply_markup=keyboard)
    
@router.callback_query(F.data.startswith("admin_ban_ad_ts_"))
async def admin_ban_ad_ts(callback: CallbackQuery, bot: Bot):
    user_id = callback.data[16:]
    async with async_session() as session:
            await ban_ad_ts(db=session, user_id=user_id)

    await bot.send_message(user_id, "⚠️ Ваше объявление в разделе «Поиск команды» было заблокировано модератором. \nКупите разблокировку за кристаллы или напишите о разблокировке в нашем <a href='https://t.me/bs_searcher'>канале</a>")
    await callback.message.answer("✅ Объявление успешно заблокировано.")

@router.callback_query(F.data.startswith("admin_ban_ad_cs_"))
async def admin_ban_ad_ts(callback: CallbackQuery, bot: Bot):
    user_id = callback.data[16:]
    async with async_session() as session:
            await ban_ad_ts(db=session, user_id=user_id)

    await bot.send_message(user_id, "⚠️ Ваше объявление в разделе «Поиск клуба» было заблокировано модератором. \nКупите разблокировку за кристаллы или напишите о разблокировке в нашем <a href='https://t.me/bs_searcher'>канале</a>")
    await callback.message.answer("✅ Объявление успешно заблокировано.")


@router.callback_query(F.data == "unban_user_admin")
async def unban_user_admin(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminPanel.get_user_id_unban)

    await callback.message.edit_text("Введите id пользователя:")

@router.message(AdminPanel.get_user_id_unban)
async def get_user_id_unban_ad(message: Message, state: FSMContext):
    user_id = message.text
    keyboard = CreateInlineButtons(count=2, text=["Поиск команды", "Поиск клуба"], callback=[f"admin_unban_ad_ts_{user_id}", f"admin_unban_ad_cs_{user_id}"], adjust=1).keyboard()
    await state.clear()
    await message.answer("Где находится объявление которое вы хотите разблокировать?",
                                     reply_markup=keyboard)

@router.callback_query(F.data.startswith("admin_unban_ad_ts_"))
async def admin_unban_ad_ts(callback: CallbackQuery, bot: Bot):
    user_id = callback.data[18:]
    async with async_session() as session:
            await unban_ad_ts(db=session, user_id=user_id)

    await bot.send_message(user_id, "⚠️ Ваше объявление в разделе «Поиск команды» было разблокировано модератором. \nПросим больше не нарушать правила.")
    await callback.message.answer("✅ Объявление успешно разблокировано.")

@router.callback_query(F.data.startswith("admin_unban_ad_cs_"))
async def admin_unban_ad_cs(callback: CallbackQuery, bot: Bot):
    user_id = callback.data[18:]
    async with async_session() as session:
            await unban_ad_cs(db=session, user_id=user_id)

    await bot.send_message(user_id, "⚠️ Ваше объявление в разделе «Поиск клуба» было разблокировано модератором. \nПросим больше не нарушать правила.")
    await callback.message.answer("✅ Объявление успешно разблокировано.")

@router.callback_query(F.data == "get_ad_by_user_id")
async def get_ad_by_user_id(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminPanel.get_ad_by_user_id)

    await callback.message.edit_text("Введите id пользователя:")

@router.message(AdminPanel.get_ad_by_user_id)
async def get_ad_by_user_id_start(message: Message, state: FSMContext):
    user_id = message.text
    keyboard = CreateInlineButtons(count=2, text=["Поиск команды", "Поиск клуба"], callback=[f"admin_get_ad_ts_{user_id}", f"admin_get_ad_cs_{user_id}"], adjust=1).keyboard()
    await state.clear()
    await message.answer("Где находится объявление которое вы хотите посмотреть?",
                                     reply_markup=keyboard)

@router.callback_query(F.data.startswith("admin_get_ad_ts_"))
async def admin_get_ad_ts(callback: CallbackQuery):
    user_id = callback.data[16:]
    async with async_session() as session:
            ad_info = await read_ad_ts_by_user_id(db=session, user_id=user_id)

    image = ad_info["image"]
    video = ad_info["video"]
    gif = ad_info["gif"] 

    if image: 
        await callback.message.answer_photo(photo=image, caption=ad_info["description"])
    if video: 
        await callback.message.answer_video(video=video, caption=ad_info["description"])
    if gif: 
        await callback.message.answer_animation(animation=gif, caption=ad_info["description"])

@router.callback_query(F.data.startswith("admin_get_ad_cs_"))
async def admin_get_ad_cs(callback: CallbackQuery, bot: Bot):
    user_id = callback.data[16:]
    async with async_session() as session:
            ad_info = await read_ad_cs_by_user_id(db=session, user_id=user_id)

    image = ad_info["image"]
    video = ad_info["video"]
    gif = ad_info["gif"] 

    if image: 
        await callback.message.answer_photo(photo=image, caption=ad_info["description"])
    if video: 
        await callback.message.answer_video(video=video, caption=ad_info["description"])
    if gif: 
        await callback.message.answer_animation(animation=gif, caption=ad_info["description"])

@router.callback_query(F.data.startswith("buy_unban_"))
async def buy_unban(callback: CallbackQuery):
    where_ban = callback.data[10:]

    if where_ban == "ts":
        keyboard = CreateInlineButtons(count=2, text=["🛒 Купить", "⬅️ Назад"], callback=["buy_unban_by_crystals_ts", "my_ad_ts"], adjust=1).keyboard()
        await callback.message.edit_text("Разблокируйте возможность выкладывать объявления в разделе «Поиск команды» за 150 💎",
                                         reply_markup=keyboard)
        return 
    if where_ban == "cs":
        keyboard = CreateInlineButtons(count=2, text=["🛒 Купить", "⬅️ Назад"], callback=["buy_unban_by_crystals_cs", "my_ad_ts"], adjust=1).keyboard()
        await callback.message.edit_text("Разблокируйте возможность выкладывать объявления в разделе «Поиск клуба» за 150 💎",
                                         reply_markup=keyboard)
        return 
    
@router.callback_query(F.data.startswith("buy_unban_by_crystals_"))
async def buy_unban_end(callback: CallbackQuery):
    user_id = callback.from_user.id 
    where_ban = callback.data[22:]

    async with async_session() as session:
        crystals_count = await read_crystals_count(db=session, user_id=user_id)

    if crystals_count < 150:
        keyboard = CreateInlineButtons(count=2, text=["🛒 Пополнить", "⬅️ Назад"], callback=["top up", "back_to_commands"], adjust=1).keyboard()
        await callback.message.edit_text("У вас недостаточно кристаллов!",
                                         reply_markup=keyboard)
        return

    async with async_session() as session:
        await crystals_substraction(db=session, user_id=user_id, deductible_crystals=150)

    if where_ban == "ts":
        async with async_session() as session:
            await unban_ad_ts(db=session, user_id=user_id)
    if where_ban == "cs":
        async with async_session() as session:
            await unban_ad_cs(db=session, user_id=user_id)

    keyboard = CreateInlineButtons(count=1, text=["Назад"], callback=["back_to_commands"], adjust=1).keyboard()
    await callback.message.edit_text("Вы разблокированы! \nПросим больше не нарушать наши правила.")