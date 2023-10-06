import os
import openai
import re

from apps.strains.models import Strain, Feeling, Negative, Flavor, HelpsWith
from apps.strains.localizations import feelings_translation, helps_with_translation, flavors_translation, negatives_translator

openai.api_key = os.environ.get('OPENAI_API_KEY')

QUESTIONS = [
    "What effect are you looking for?",
    "Are there any negative effects you'd like to avoid?",
    "Do you have a preference for the type of plant (Sativa, Indica, Hybrid)?",
    "Are there specific medicinal properties you are looking for?",
    "What levels of CBD and THC are you seeking?",
    "Do you have specific flavors you prefer?"
]

CONTEXT = (f"You are a helpful budtender. You need to sequentially ask questions from the list: {QUESTIONS}"
           f"Each question should be asked separately, and the next question should only be posed "
           f"after receiving an answer to the previous one. Once you've received answers "
           f"to all the questions, you need to identify patterns and connections between "
           f"the user's answers and the values found in the constants files:"
           f"{feelings_translation}, {helps_with_translation}, {flavors_translation}, {negatives_translator}"
           f"After selecting the appropriate values, execute a database query to obtain a django "
           f"queryset for the model {Strain} and possible {Flavor} {Feeling} {Negative} {HelpsWith} using the filter method. "
           f"You can try mixing filter parameters until the queryset consists of at least "
           f"three items. Then, return a list of three items "
           f"(cannabis strains using the name field of the Strain model) to the user.")


MAX_MESSAGES = 10
INIT_MESSAGE = {"role": "system", "content": QUESTIONS[0]}
QUESTION_INDEX = 1  # Start with the first question, as 0 is already in INIT_MESSAGE


def chatbot(user_messages):
    global QUESTION_INDEX

    messages = [
        {"role": "system", "content": CONTEXT}
    ]
    print(f'user_messages: {user_messages}')
    messages.extend(user_messages)

    # Обрезаем историю сообщений, если она становится слишком длинной
    if len(messages) > MAX_MESSAGES:
        messages = messages[-MAX_MESSAGES:]

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        max_tokens=150,
        temperature=0.6
    )
    user_responses = [msg for msg in user_messages if msg['role'] == 'user']

    chat_message = response['choices'][0]['message']['content']

    if len(user_responses) < len(QUESTIONS):
        chat_message = QUESTIONS[QUESTION_INDEX]
        QUESTION_INDEX += 1
        return chat_message
    else:
        filters = analyze_user_responses(user_messages)
        return get_recommended_strains(filters)

    # if len(user_messages) < len(QUESTIONS):
    #     chat_message = QUESTIONS[QUESTION_INDEX]
    #     QUESTION_INDEX += 1
    #     return chat_message
    # else:
    #     filters = analyze_user_responses(user_messages)
    #     recommended_strains = get_recommended_strains(filters)
    #     return recommended_strains

def analyze_user_responses(user_messages):
    filters = {}

    # Получение всех ответов пользователя
    user_responses = [msg['content'].lower() for msg in user_messages if msg['role'] == 'user']

    # Анализ ответа на вопрос о эффекте
    feelings_response = user_responses[0]
    for english, spanish in feelings_translation.items():
        if spanish in feelings_response:
            feeling = Feeling.objects.filter(name=english).first()
            if feeling:
                filters['feelings'] = feeling
        elif any(word in feelings_response for word in spanish.split()):
            feeling = Feeling.objects.filter(name=english).first()
            if feeling:
                filters['feelings'] = feeling

    # Анализ ответа на вопрос о негативных эффектах
    negatives_response = user_responses[1]
    for english, spanish in negatives_translator.items():
        if spanish in negatives_response:
            negative = Negative.objects.filter(name=english).first()
            if negative:
                filters['negatives'] = negative
        elif any(word in negatives_response for word in spanish.split()):
            negative = Negative.objects.filter(name=english).first()
            if negative:
                filters['negatives'] = negative

    # Анализ ответа на вопрос о типе растения
    type_response = user_responses[2]
    if "sativa" in type_response:
        filters['category'] = 'Sativa'
    elif "indica" in type_response:
        filters['category'] = 'Indica'
    elif "hybrid" in type_response:
        filters['category'] = 'Hybrid'

    # Анализ ответа на вопрос о лечебных свойствах
    helps_with_response = user_responses[3]
    for english, spanish in helps_with_translation.items():
        if spanish in helps_with_response:
            helps_with = HelpsWith.objects.filter(name=english).first()
            if helps_with:
                filters['helps_with'] = helps_with
        elif any(word in helps_with_response for word in spanish.split()):
            helps_with = HelpsWith.objects.filter(name=english).first()
            if helps_with:
                filters['helps_with'] = helps_with

    # Анализ уровней THC
    thc_response = user_responses[4]
    thc_match = re.search(r"(\d+)%", thc_response)
    if thc_match:
        thc_percentage = int(thc_match.group(1))
        filters['thc'] = thc_percentage

    # Анализ ответа на вопрос о вкусах
    flavors_response = user_responses[5]
    for english, spanish in flavors_translation.items():
        if spanish in flavors_response:
            flavor = Flavor.objects.filter(name=english).first()
            if flavor:
                filters['flavors'] = flavor
        elif any(word in flavors_response for word in spanish.split()):
            flavor = Flavor.objects.filter(name=english).first()
            if flavor:
                filters['flavors'] = flavor

    return filters


def get_recommended_strains(filters):
    strains = Strain.objects.all()
    print(f'filters: {filters}')
    if 'feelings' in filters:
        strains = strains.filter(feelings=filters['feelings'])
    if 'negatives' in filters:
        strains = strains.exclude(negatives=filters['negatives'])
    if 'category' in filters:
        strains = strains.filter(category=filters['category'])
    if 'helps_with' in filters:
        strains = strains.filter(helps_with=filters['helps_with'])
    if 'flavors' in filters:
        strains = strains.filter(flavors=filters['flavors'])
    recommended_strains = [strain.name for strain in strains[:3]]
    return ", ".join(recommended_strains)

