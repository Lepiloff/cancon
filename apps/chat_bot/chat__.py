from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
from apps.strains.models import Strain
from nltk.stem import SnowballStemmer

stemmer = SnowballStemmer("english")
QUESTIONS = [
    "What effect are you looking for?",
    "Are there any negative effects you'd like to avoid?",
    "Do you have a preference for the type of plant (Sativa, Indica, Hybrid)?",
    "Are there specific medicinal properties you are looking for?",
    "What levels of CBD and THC are you seeking?",
    "Do you have specific flavors you prefer?"
]

def initialize_products():
    strains = Strain.objects.filter(active=True).prefetch_related('feelings', 'negatives', 'helps_with', 'flavors', 'dominant_terpene', 'other_terpenes')
    products = []

    for strain in strains:
        product_info = {
            "id": strain.id,
            "name": strain.name,
            "description": strain.description,
            "cbd": strain.cbd,
            "thc": strain.thc,
            "cbg": strain.cbg,
            "category": strain.category,
            "feelings": [feeling.name for feeling in strain.feelings.all()],
            "negatives": [negative.name for negative in strain.negatives.all()],
            "helps_with": [helps.name for helps in strain.helps_with.all()],
            "flavors": [flavor.name for flavor in strain.flavors.all()],
            "dominant_terpene": strain.dominant_terpene.name if strain.dominant_terpene else None,
            "other_terpenes": [terpene.name for terpene in strain.other_terpenes.all()],
            "slug": strain.slug
        }

        # Расширяем текст для векторизации
        combined_text = f"{product_info['name']} {product_info['description']} {product_info['cbd']} {product_info['thc']} {product_info['cbg']} {product_info['category']} {' '.join(product_info['feelings'])} {' '.join(product_info['negatives'])} {' '.join(product_info['helps_with'])} {' '.join(product_info['flavors'])} {product_info['dominant_terpene']} {' '.join(product_info['other_terpenes'])}"

        # Применяем стемминг к тексту
        combined_text = " ".join([stemmer.stem(word) for word in combined_text.split()])

        product_info['combined_text'] = combined_text
        products.append(product_info)

    return products

products = initialize_products()

# Используем веса для разных полей
def custom_preprocessor(text):
    # Увеличиваем вес для категории сорта
    category_weight = 3
    text = text.replace("Sativa", "Sativa " * category_weight)
    text = text.replace("Indica", "Indica " * category_weight)
    text = text.replace("Hybrid", "Hybrid " * category_weight)
    return text

vectorizer = TfidfVectorizer(stop_words='english')
tfidf_matrix = vectorizer.fit_transform([product['description'] for product in products])


def chatbot(user_message):
    # Применяем стемминг к запросу пользователя
    user_message = " ".join([stemmer.stem(word) for word in user_message.split()])

    # Преобразуйте запрос пользователя в TF-IDF вектор
    user_vector = vectorizer.transform([user_message])

    # Вычислите косинусное сходство между запросом пользователя и каждым продуктом
    cosine_similarities = linear_kernel(user_vector, tfidf_matrix).flatten()

    # Получите индексы трех наиболее похожих продуктов
    top_indices = cosine_similarities.argsort()[-3:][::-1]

    # Construct the response message based on the top products
    response_message = "I recommend checking out the following strains based on your preferences:<br>"
    for index in top_indices:
        product = products[index]
        product_name = product['name']
        product_slug = product['slug']
        response_message += f'<a href="/strain/{product_slug}/">{product_name}</a><br>'

    return response_message
