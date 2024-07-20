import os
import openai
import csv
import io
import time
import re

from django.core.cache import cache
from apps.strains.models import Strain

openai.api_key = os.environ.get('OPENAI_API_KEY')

QUESTIONS = [
    "What effect are you looking for?",
    "Are there any negative effects you'd like to avoid?",
    "Do you have a preference for the type of plant (Sativa, Indica, Hybrid)?",
    "Are there specific medicinal properties you are looking for?",
    "What levels of CBD and THC are you seeking?",
    "Do you have specific flavors you prefer?"
]

def generate_product_csv():
    cache_key = "product_csv"
    cache_key_count = "product_count"

    # Проверка кеша
    cached_csv = cache.get(cache_key)
    cached_count = cache.get(cache_key_count)

    current_count = Strain.objects.filter(active=True).count()

    if cached_csv and cached_count == current_count:
        return cached_csv

    # Если кеш отсутствует или данные изменились, формируем новый CSV
    strains = Strain.objects.filter(active=True).prefetch_related('feelings', 'negatives',
                                                                  'helps_with', 'flavors',
                                                                  'dominant_terpene',
                                                                  'other_terpenes')

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(
        ["Name", "THC", "CBD", "Category", "Effects", "Negatives", "Helps With", "Flavors",
         "Slug"])

    for strain in strains:
        row = [
            strain.name,
            strain.thc,
            strain.cbd,
            strain.category,
            ', '.join(feeling.name for feeling in strain.feelings.all()),
            ', '.join(negative.name for negative in strain.negatives.all()),
            ', '.join(help.name for help in strain.helps_with.all()),
            ', '.join(flavor.name for flavor in strain.flavors.all()),
            strain.slug
        ]
        writer.writerow(row)

    product_csv = output.getvalue()

    # Сохраняем данные в кеш
    cache.set(cache_key, product_csv, timeout=60*60)  # Кеш на 1 час
    cache.set(cache_key_count, current_count, timeout=60*60)

    return product_csv

def parse_product_csv(product_csv):
    reader = csv.DictReader(io.StringIO(product_csv))
    strains = []
    for row in reader:
        strains.append({
            "name": row["Name"],
            "thc": row["THC"],
            "cbd": row["CBD"],
            "category": row["Category"],
            "effects": row["Effects"],
            "negatives": row["Negatives"],
            "helps_with": row["Helps With"],
            "flavors": row["Flavors"],
            "slug": row["Slug"]
        })
    return strains

def chatbot(user_message, chat_history, retry_count=1):
    product_csv = generate_product_csv()
    strains = parse_product_csv(product_csv)

    system_message = {
        "role": "system",
        "content": "You are a chatbot helping customers choose cannabis strains. "
                   "Use only the provided product data to answer questions. "
                   "Here is the available product data in CSV format:\n" + product_csv +
                   "\nAnswer in a list format with up to 5 recommendations based on the user's preferences. "
                   "Match user preferences to the corresponding fields: 'feelings', 'negatives', 'helps_with', 'flavors', 'category', 'thc'. "
                   "If a question is not related to cannabis strains, respond that it is outside your expertise."
    }

    messages = [system_message] + chat_history + [{"role": "user", "content": user_message}]

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=300,  # Уменьшение количества токенов
            temperature=0.5  # Более низкая температура для стабильности ответов
        )

        bot_response = response.choices[0].message['content']

        for strain in strains:
            product_name = strain["name"]
            product_slug = strain["slug"]
            # Используем регулярное выражение для точного соответствия имени сорта
            pattern = re.compile(r'\b{}\b'.format(re.escape(product_name)))
            link = f'<a href="/strain/{product_slug}/">{product_name}</a>'
            bot_response = pattern.sub(link, bot_response)

        return bot_response
    except (openai.error.RateLimitError, openai.error.APIError, openai.error.InvalidRequestError) as e:
        if retry_count > 0:
            time.sleep(20)
            return chatbot(user_message, chat_history, retry_count=retry_count-1)
        else:
            return "Sorry, I'm experiencing technical difficulties. Please try again later."
