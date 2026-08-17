import os
import asyncio
from fastapi import FastAPI
import uvicorn
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import BufferedInputFile
from rembg import remove

BOT_TOKEN = os.getenv("BOT_TOKEN", "8831926804:AAF707FDwRYHQ3zthsMHfbXqUq-p_7rBbYE")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
app = FastAPI()

@app.get("/")
def home():
    return {"status": "Bot is running 24/7 on Render!"}

@dp.message(CommandStart())
async def start_handler(message: types.Message):
    await message.answer(
        "Салом! Ба ман як расм (акс) фиристед, то ман пасзаминаи (фон) онро тоза карда ба шумо баргардонам."
    )

@dp.message(F.photo)
async def handle_photo(message: types.Message):
    wait_msg = await message.answer("Лутфан каме интизор шавед, пасзаминаи акс тоза карда истодааст... ⏳")
    
    try:
        photo = message.photo[-1]
        file_info = await bot.get_file(photo.file_id)
        file_bytes_io = await bot.download_file(file_info.file_path)
        
        input_bytes = file_bytes_io.read()
        
        # Коркарди акс дар пасманзар (background thread), то ки бот қафо намонад
        loop = asyncio.get_running_loop()
        output_bytes = await loop.run_in_executor(None, remove, input_bytes)
        
        output_file = BufferedInputFile(output_bytes, filename="no_bg.png")
        
        await message.answer_document(
            document=output_file,
            caption="Марҳамат, пасзаминаи акси шумо бомуваффақият тоза карда шуд! ✨"
        )
        
        await bot.delete_message(chat_id=message.chat.id, message_id=wait_msg.message_id)
        
    except Exception as e:
        await message.answer(f"Ҳангоми коркарди акс хатогӣ рух дод: {e}")

async def main():
    port = int(os.environ.get("PORT", 10000))
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    
    # Фавран кушодани порт барои Render ва ба кор андохтани бот
    await asyncio.gather(
        server.serve(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())