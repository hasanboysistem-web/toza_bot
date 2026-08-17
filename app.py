import os
import asyncio
import logging
import subprocess
import tempfile
import cv2
import numpy as np
from rembg import remove, new_session
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import FSInputFile
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.client.session.aiohttp import AiohttpSession  # Иловаи нав барои ислоҳи вақт

# ==========================================
# 1. ТАНЗИМОТИ БОТ ВА МОДЕЛИ AI
# ==========================================
# ДИҚҚАТ: Дар ин ҷо токени худро гузоред!
BOT_TOKEN = "8831926804:AAF707FDwRYHQ3zthsMHfbXqUq-p_7rBbYE"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

logger.info("⏳ Модели AI (u2netp) дар ҳоли омодашавӣ...")
# Модели сабукро як бор фаъол мекунем, то расмҳо фавран коркард шаванд
session = new_session("u2netp")
logger.info("✅ Модели AI муваффақона омода шуд!")

# ИСЛОҲИ НАВ: Вақти интизориро то 600 сония (10 дақиқа) зиёд мекунем
bot_session = AiohttpSession(timeout=600)
bot = Bot(token=BOT_TOKEN, session=bot_session, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# ==========================================
# 2. ФУНКСИЯҲОИ КОРКАРДИ РАСМ ВА ВИДЕО
# ==========================================
def process_image(input_path: str, output_path: str):
    """Коркарди расм бо истифодаи модели сабук ва сессияи тайёр"""
    with open(input_path, 'rb') as i:
        input_data = i.read()
    
    output_data = remove(input_data, session=session)
    
    with open(output_path, 'wb') as o:
        o.write(output_data)

def process_video(input_path: str, output_path: str):
    """Коркарди видео кадр ба кадр бо нишон додани пешрафт"""
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise Exception("Хатогӣ ҳангоми кушодани видео.")

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    logger.info(f"🎥 Оғози коркард: {total_frames} кадр, {width}x{height} пиксел")

    temp_video_path = output_path + "_temp.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(temp_video_path, fourcc, fps, (width, height))

    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_count += 1
        if frame_count % 10 == 0 or frame_count == total_frames:
            logger.info(f"⏳ Кадри {frame_count} аз {total_frames} коркард шуд...")
        
        # Коркарди ҳар як кадр
        out_frame_rgba = remove(frame, session=session)
        out_frame_bgr = cv2.cvtColor(out_frame_rgba, cv2.COLOR_RGBA2BGR)
        out.write(out_frame_bgr)

    cap.release()
    out.release()

    # Илова кардани овоз бо ёрии FFmpeg
    try:
        subprocess.run([
            'ffmpeg', '-y', '-i', temp_video_path, '-i', input_path,
            '-c:v', 'copy', '-c:a', 'aac', '-map', '0:v:0', '-map', '1:a:0?',
            '-shortest', output_path
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)
    except Exception as e:
        logger.warning(f"Овоз часпонида нашуд (FFmpeg нест ё хатогӣ): {e}")
        if os.path.exists(temp_video_path):
            os.rename(temp_video_path, output_path)

# ==========================================
# 3. ФАРМОНҲОИ БОТ (HANDLERS)
# ==========================================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        f"Салом <b>{message.from_user.first_name}</b>! 👋\n\n"
        "Ба ман ягон расм ё видео фиристед, то пасзаминаи (фони) онро тоза кунам."
    )

@dp.message(F.photo)
async def handle_photo(message: types.Message):
    wait_msg = await message.answer("⏳ Расм қабул шуд. Коркард рафта истодааст...")
    
    with tempfile.TemporaryDirectory() as tmpdirname:
        input_file = os.path.join(tmpdirname, f"in_{message.message_id}.jpg")
        output_file = os.path.join(tmpdirname, f"out_{message.message_id}.png")
        
        try:
            # Боргирии расм
            photo_size = message.photo[-1]
            await bot.download(photo_size, destination=input_file)
            
            # Коркард
            await asyncio.to_thread(process_image, input_file, output_file)
            
            # Фиристодани натиҷа
            document = FSInputFile(output_file, filename="transparent_image.png")
            await message.answer_document(document=document, caption="✅ Тайёр!")
            
        except Exception as e:
            logger.error(f"Хатогии расм: {e}")
            await message.answer("❌ Ҳангоми коркарди расм хатогӣ рух дод.")
        finally:
            await wait_msg.delete()

@dp.message(F.video)
async def handle_video(message: types.Message):
    wait_msg = await message.answer("⏳ Видео қабул шуд. Лутфан сабр кунед, ин каме вақт мегирад...")
    
    with tempfile.TemporaryDirectory() as tmpdirname:
        input_file = os.path.join(tmpdirname, f"in_{message.message_id}.mp4")
        output_file = os.path.join(tmpdirname, f"out_{message.message_id}.mp4")
        
        try:
            # Боргирии видео
            await bot.download(message.video, destination=input_file)
            
            # Коркард
            await asyncio.to_thread(process_video, input_file, output_file)
            
            # Фиристодани натиҷа бо вақти зиёдшуда
            video_doc = FSInputFile(output_file, filename="no_bg_video.mp4")
            await message.answer_video(video=video_doc, caption="✅ Видеои шумо тайёр!")
            
        except Exception as e:
            logger.error(f"Хатогии видео: {e}")
            await message.answer("❌ Ҳангоми коркарди видео хатогӣ рух дод.")
        finally:
            await wait_msg.delete()

async def main():
    logger.info("Бот фаъол шуд!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот қатъ гардид.")