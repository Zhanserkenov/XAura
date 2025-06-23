import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# --- Загрузка данных о продуктах из .txt ---
def load_products(file_path="products.txt"):
    with open(file_path, "r", encoding="utf-8") as f:
        data = f.read().strip()

    products = []
    for block in data.split("\n\n"):
        lines = block.strip().split("\n")
        product = {}
        for line in lines:
            if line.startswith("Название:"):
                product["name"] = line.replace("Название:", "").strip()
            elif line.startswith("Описание:"):
                product["description"] = line.replace("Описание:", "").strip()
            elif line.startswith("Изображение:"):
                product["image"] = line.replace("Изображение:", "").strip()
        products.append(product)
    return products

PRODUCTS = load_products()

DISEASE_IMAGE_MAP = {
    "грыжа шейного диска": "images/neck_hernia.png",
    "поясничная грыжа": "images/lumbar_hernia.png",
    "мышечные и суставные боли": "images/muscle_joint_pain.png",
    "разрыв мениска": "images/meniscus.png",
    "ревматизм": "images/rheumatism.png",
    "потеря жидкости в коленях": "images/knee_fluid_loss.png",
    "беспокойные ноги": "images/restless_legs.png",
    "кальцификация": "images/calcification.png",
    "онемение и слабость": "images/numbness.png",
    "сахарный диабет": "images/diabetes.png",
    "мигрень": "images/migraine.png",
    "артериальное давление": "images/blood_pressure.png",
    "псориаз": "images/psoriasis.png",
    "экзема": "images/psoriasis.png",
    "рожа": "images/psoriasis.png",
    "варикозное расширение вен": "images/varicose.png",
    "свертывание крови": "images/clotting.png",
    "зоб": "images/goiter.png",
    "астма": "images/asthma.png",
    "бронхит": "images/asthma.png",
    "хобл": "images/asthma.png",
    "фибромиалгия": "images/fibromyalgia.png",
    "рассеянный склероз": "images/ms.png",
    "эпилепсия": "images/epilepsy.png",
    "средиземноморская анемия": "images/anemia.png",
    "паркинсона": "images/parkinson.png",
    "головокружение": "images/dizziness.png",
    "проблемы со сном": "images/sleep.png",
    "концентрация внимания": "images/focus.png",
    "гинекологические заболевания": "images/gynecology.png",
    "мужские болезни": "images/male.png",
    "альцгеймер": "images/alzheimer.png",
    "витилиго": "images/vitiligo.png"
}

def get_products_text():
    return "\n\n".join([f"{p['name']}: {p['description']}" for p in PRODUCTS])


# --- Обращение к Gemini через REST API ---
def ask_gemini(user_input: str, product_info: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {
        "Content-Type": "application/json"
    }

    prompt = f"""Ты — консультант по продуктам. Отвечай кратко и понятно.
Информация о продуктах:
{product_info}

Вопрос клиента: {user_input}
"""

    body = {
        "contents": [
            {
                "parts": [
                    { "text": prompt }
                ]
            }
        ]
    }

    response = requests.post(url, headers=headers, json=body)
    if response.ok:
        try:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        except Exception:
            return "Ошибка при обработке ответа Gemini."
    else:
        return f"Ошибка при запросе к Gemini API: {response.status_code}"

def is_equivalent_with_gemini(user_text: str, disease_name: str) -> bool:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {
        "Content-Type": "application/json"
    }

    prompt = f"""
Ответь "Да" или "Нет". Считается ли запрос "{user_text}" эквивалентным заболеванию "{disease_name}"?
Не объясняй. Просто ответь: Да или Нет.
"""

    body = {
        "contents": [
            {
                "parts": [
                    { "text": prompt }
                ]
            }
        ]
    }

    response = requests.post(url, headers=headers, json=body)
    if response.ok:
        try:
            answer = response.json()['candidates'][0]['content']['parts'][0]['text'].strip().lower()
            return answer.startswith("да")
        except Exception:
            return False
    return False

# --- Ответ пользователю в Telegram ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    product_text = get_products_text()
    reply = ask_gemini(user_input, product_text)

    for disease, image_path in DISEASE_IMAGE_MAP.items():
        if is_equivalent_with_gemini(user_input, disease):
            if os.path.exists(image_path):
                with open(image_path, "rb") as img:
                    await update.message.reply_photo(photo=img, caption=reply)
                    return

    await update.message.reply_text(reply)


# --- Запуск Telegram-бота ---
app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

if __name__ == "__main__":
    print("Бот запущен...")
    app.run_polling()
