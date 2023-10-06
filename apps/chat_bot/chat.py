import os
import openai
import csv
import io
import time

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
    strains = Strain.objects.filter(active=True).prefetch_related('feelings', 'negatives',
                                                                  'helps_with', 'flavors',
                                                                  'dominant_terpene',
                                                                  'other_terpenes')

    output = io.StringIO()
    writer = csv.writer(output)

    # Заголовок CSV
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

    return output.getvalue()


def chatbot(user_message, retry_count=1):
    product_csv = generate_product_csv()

    # Construct the message objects for ChatGPT API
    message_objects = [
        {
            "role": "system",
            "content": "You're a budtender chatbot helping customers with product recommendations."
                       " Here's the available product data in CSV format: " + product_csv +
                       " You must use only strains from this data to answer customer questions. "
                       " Provide recommendations in a list format, with up to 5 strains."
                       " For each strain, include its name, THC and CBD levels, "
                       " flavors, and effects."
                       " Your responses should be limited to the topic of cannabis. "
                       " For all questions on subjects not related to cannabis strains, "
                       " you should reply that such topics are not within your expertise."
        },
        {"role": "user", "content": user_message}
    ]

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-16k",
            messages=message_objects,
            max_tokens=500,
            temperature=0.6
        )

        # Extract the bot's response
        bot_response = response.choices[0].message['content']

        # Replace product names with links using slug
        strains = Strain.objects.filter(active=True)
        for strain in strains:
            product_name = strain.name
            product_slug = strain.slug
            link = f'<a href="/strain/{product_slug}/">{product_name}</a>'
            bot_response = bot_response.replace(product_name, link)

        return bot_response
    except (openai.error.RateLimitError, openai.error.APIError, openai.error.InvalidRequestError) as e:
        if retry_count > 0:
            time.sleep(20)
            return chatbot(user_message, retry_count=retry_count-1)
        else:
            return "Sorry, I'm experiencing technical difficulties. Please try again later."

