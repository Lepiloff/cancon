 # SEO Multi-Language Implementation Guide

**Критически важно:** Сохранить текущую SEO индексацию испанского контента!

---

## Текущая проблема

### ❌ Как работает СЕЙЧАС:
```
URL: /strain/northern-lights/
- Язык сессии ES → показывает испанский контент
- Язык сессии EN → показывает английский контент

Проблемы:
1. Один URL, разный контент → Google не знает какой язык индексировать
2. Нет hreflang тегов → Google не знает о связи версий
3. Language switcher меняет только сессию, не URL
4. Невозможно проиндексировать обе версии одновременно
5. Дублированный контент (duplicate content) для поисковиков
```

### Google видит:
```
GET /strain/northern-lights/
Раз 1: испанский контент
Раз 2: английский контент
Раз 3: испанский контент
→ Confusion! Какой язык индексировать?
```

---

## ✅ Решение: i18n_patterns с prefix_default_language=False

### Как будет работать ПОСЛЕ:
```
Испанский (default):  /strain/northern-lights/         ← Текущий URL (сохраняется!)
Английский (новый):   /en/strain/northern-lights/      ← Новый URL

Google видит:
- /strain/northern-lights/      → всегда ES (испанский)
- /en/strain/northern-lights/   → всегда EN (английский)
- hreflang теги связывают их
```

### Преимущества:
- ✅ **Сохраняет ВСЕ текущие испанские URL** → SEO не пострадает
- ✅ Создает новые английские URL с префиксом /en/
- ✅ Каждый URL = один язык = чистая индексация
- ✅ hreflang теги сообщают Google о связи версий
- ✅ Обратная совместимость (старые ссылки продолжают работать)

---

## ⚠️ Критические риски и улучшения (АУДИТ)

### 1. ❌ Хрупкая логика slice:'3:' в шаблонах

**Проблема:** Ручное обрезание префикса `/en/` через `slice:'3:'` ломается при:
- Других языках (fr, de)
- Изменении структуры URL
- Query-параметрах
- Вложенных путях

**Решение:** Использовать `{% translate_url %}` для генерации URL нужного языка.

```django
{# ❌ Хрупко #}
<link rel="alternate" hreflang="es" href="https://cannamente.com{{ request.path|slice:'3:' }}">

{# ✅ Правильно #}
<link rel="alternate" hreflang="es" href="{{ request.scheme }}://{{ request.get_host }}{% translate_url 'es' %}">
```

---

### 2. ⚠️ Стратегия x-default

**Текущее решение:** x-default указывает на ES-страницу.

**Лучше:**
- Если есть отдельная страница выбора языка → x-default туда
- Если нет → x-default на дефолтный ES (текущий вариант OK)
- **Главное:** быть последовательным на ВСЕХ страницах

**Рекомендация:** Оставить x-default на ES как дефолт для всех страниц.

---

### 3. 🚨 hreflang В SITEMAP (не только HTML!)

**Критически важно:** Google лучше понимает связь языков, если hreflang дублируется в sitemap.xml.

**Реализация:** Добавить `xmlns:xhtml` и двунаправленные ссылки в каждую запись sitemap:

```xml
<url>
  <loc>https://cannamente.com/strain/northern-lights/</loc>
  <xhtml:link rel="alternate" hreflang="es" href="https://cannamente.com/strain/northern-lights/" />
  <xhtml:link rel="alternate" hreflang="en" href="https://cannamente.com/en/strain/northern-lights/" />
  <xhtml:link rel="alternate" hreflang="x-default" href="https://cannamente.com/strain/northern-lights/" />
  <lastmod>2025-10-10</lastmod>
</url>
```

**Класс I18nSitemap:** См. раздел "Пошаговая реализация" ниже.

---

### 4. ❌ Генерация путей строками в sitemap

**Проблема:**
```python
def location(self, obj):
    return f'/en/strain/{obj.slug}/'  # Хрупко!
```

**Решение:** Использовать `reverse()` с `translation.override()`:

```python
from django.urls import reverse
from django.utils import translation

def location(self, obj):
    with translation.override('en'):
        return reverse('strain_detail', kwargs={'slug': obj.slug})
```

---

### 5. ⚠️ Canonical и query-параметры

**Проблема:** `<link rel="canonical" href="{{ request.path }}">` включает query-строку (utm, filters, page).

**Решение:** Очистить canonical от query-параметров:

```django
{# В base.html #}
<link rel="canonical" href="{{ request.scheme }}://{{ request.get_host }}{{ request.path }}">
```

Для страниц с пагинацией:
- `/strains/?page=1` → canonical на `/strains/` (первая страница)
- `/strains/?page=2` → canonical на `/strains/?page=2` + добавить `rel="prev"/"next"`

---

### 6. 🚫 НЕ делать авторедирект по гео/браузеру!

**Приоритет языка:**
1. URL (если есть `/en/` → всегда EN)
2. Cookie/сессия пользователя
3. Accept-Language header (только как fallback)

**НЕ ДЕЛАТЬ:**
```python
# ❌ Плохо
if request.META.get('HTTP_ACCEPT_LANGUAGE', '').startswith('en'):
    return redirect('/en' + request.path)
```

Это вызовет:
- "Мигающую" локализацию
- Жалобы Search Console на несоответствие контента
- Проблемы с кешированием

---

### 7. 🔄 Middleware для редиректа EN-сессии на ES-пути

**Проблема:** Если раньше английский контент показывался на испанских URL через сессию, могут остаться битые кэши.

**Решение:** Middleware для редиректа:

```python
# canna/middleware.py
from django.shortcuts import redirect
from django.utils import translation

class LanguageUrlRedirectMiddleware:
    """Redirect EN session on ES path to proper /en/ URL"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        current_lang = translation.get_language()
        path = request.path

        # Если EN язык, но путь без /en/ → редирект
        if current_lang == 'en' and not path.startswith('/en/'):
            # Исключения: admin, i18n, static, media
            if not any(path.startswith(p) for p in ['/admin/', '/i18n/', '/static/', '/media/']):
                return redirect(f'/en{path}', permanent=True)

        # Если ES язык, но путь с /en/ → редирект
        if current_lang == 'es' and path.startswith('/en/'):
            return redirect(path[3:], permanent=True)

        return self.get_response(request)
```

**Добавить в settings.py:**
```python
MIDDLEWARE = [
    # ...
    'django.middleware.locale.LocaleMiddleware',
    'canna.middleware.LanguageUrlRedirectMiddleware',  # После LocaleMiddleware!
    # ...
]
```

---

### 8. 📊 Structured Data (JSON-LD) с inLanguage

**Обновить в views:**

```python
# apps/strains/views.py
from django.utils.translation import get_language

def strain_detail(request, slug):
    strain = get_object_or_404(Strain, slug=slug, active=True)
    current_lang = get_language()

    structured_data = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": strain.name,
        "description": strain.description,  # Автоматически правильный язык
        "inLanguage": current_lang,  # 'es' или 'en'
        "@id": request.build_absolute_uri(),  # Уникальный для каждого языка
        # ...
    }
```

---

### 9. 🏷️ OpenGraph с og:locale

**Добавить в base.html:**

```django
{% load i18n %}
{% get_current_language as CURRENT_LANG %}

<!-- OpenGraph -->
<meta property="og:url" content="{{ request.build_absolute_uri }}">
<meta property="og:locale" content="{% if CURRENT_LANG == 'es' %}es_ES{% else %}en_US{% endif %}">
<meta property="og:locale:alternate" content="{% if CURRENT_LANG == 'es' %}en_US{% else %}es_ES{% endif %}">
<meta property="og:title" content="{% block og_title %}{{ title }}{% endblock %}">
<meta property="og:description" content="{% block og_description %}{{ description }}{% endblock %}">
```

---

### 10. 🗺️ Sitemap Index

**Создать главный index:**

```python
# canna/sitemaps.py
from django.contrib.sitemaps import Sitemap

class SitemapIndex(Sitemap):
    """Index of all sitemaps"""

    def items(self):
        return ['strains-es', 'strains-en', 'articles-es', 'articles-en']

    def location(self, item):
        return f'/sitemap-{item}.xml'
```

**В robots.txt:**
```
User-agent: *
Allow: /

Sitemap: https://cannamente.com/sitemap.xml
```

---

### 11. 🧪 Тесты на консистентность

**Создать:** `apps/strains/tests/test_i18n_seo.py`

```python
import pytest
from django.test import Client
from django.utils import translation
from bs4 import BeautifulSoup

@pytest.mark.django_db
class TestI18nSEO:

    def test_spanish_urls_unchanged(self, strain_factory):
        """Испанские URL должны остаться без изменений"""
        strain = strain_factory(slug='test-strain', active=True)

        client = Client()
        response = client.get('/strain/test-strain/')

        assert response.status_code == 200
        assert 'test-strain' in str(response.content)

    def test_english_urls_have_prefix(self, strain_factory):
        """Английские URL должны иметь /en/ префикс"""
        strain = strain_factory(slug='test-strain', active=True)

        client = Client()
        response = client.get('/en/strain/test-strain/')

        assert response.status_code == 200

    def test_hreflang_tags_present(self, strain_factory):
        """hreflang теги должны присутствовать"""
        strain = strain_factory(slug='test-strain', active=True)

        client = Client()
        response = client.get('/strain/test-strain/')
        soup = BeautifulSoup(response.content, 'html.parser')

        hreflang_tags = soup.find_all('link', rel='alternate', hreflang=True)

        assert len(hreflang_tags) >= 2
        languages = [tag['hreflang'] for tag in hreflang_tags]
        assert 'es' in languages
        assert 'en' in languages
        assert 'x-default' in languages

    def test_hreflang_bidirectional(self, strain_factory):
        """hreflang должен быть двунаправленным"""
        strain = strain_factory(slug='test-strain', active=True)

        client = Client()

        # На ES странице должна быть ссылка на EN
        response_es = client.get('/strain/test-strain/')
        soup_es = BeautifulSoup(response_es.content, 'html.parser')
        en_link = soup_es.find('link', hreflang='en')
        assert '/en/strain/test-strain/' in en_link['href']

        # На EN странице должна быть ссылка на ES
        response_en = client.get('/en/strain/test-strain/')
        soup_en = BeautifulSoup(response_en.content, 'html.parser')
        es_link = soup_en.find('link', hreflang='es')
        assert '/strain/test-strain/' in es_link['href']

    def test_canonical_correct(self, strain_factory):
        """Canonical должен быть без query-параметров"""
        strain = strain_factory(slug='test-strain', active=True)

        client = Client()
        response = client.get('/strain/test-strain/?utm_source=test')
        soup = BeautifulSoup(response.content, 'html.parser')

        canonical = soup.find('link', rel='canonical')
        assert 'utm_source' not in canonical['href']

    def test_sitemap_has_both_languages(self):
        """Sitemap должен содержать обе языковые версии"""
        client = Client()
        response = client.get('/sitemap.xml')

        assert b'/strain/' in response.content  # ES
        assert b'/en/strain/' in response.content  # EN

    def test_no_vary_accept_language(self, strain_factory):
        """Vary: Accept-Language не нужен для URL-стратегии"""
        strain = strain_factory(slug='test-strain', active=True)

        client = Client()
        response = client.get('/strain/test-strain/')

        assert 'Accept-Language' not in response.get('Vary', '')
```

---

## Пошаговая реализация (ОБНОВЛЕНО)

### Шаг 1: Обновить canna/urls.py

**Было:**
```python
urlpatterns = [
    path('admin/', admin.site.urls),
    path('tinymce/', include('tinymce.urls')),
    path('i18n/', include('django.conf.urls.i18n')),
    path('', include('apps.strains.urls')),
    path('store/', include('apps.store.urls')),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps},
         name='django.contrib.sitemaps.views.sitemap'),
]
```

**Стало:**
```python
from django.conf.urls.i18n import i18n_patterns

# Не требуют перевода (без префиксов)
urlpatterns = [
    path('admin/', admin.site.urls),
    path('tinymce/', include('tinymce.urls')),
    path('i18n/', include('django.conf.urls.i18n')),
]

# Мультиязычные URL (только /en/ получит префикс)
urlpatterns += i18n_patterns(
    path('', include('apps.strains.urls')),
    path('store/', include('apps.store.urls')),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps},
         name='django.contrib.sitemaps.views.sitemap'),
    prefix_default_language=False  # Испанский БЕЗ префикса!
)
```

**Результат:**
```
ES (default):  /strain/northern-lights/        ← Сохраняется
EN:            /en/strain/northern-lights/     ← Новый

ES:  /articles/                                ← Сохраняется
EN:  /en/articles/                             ← Новый

ES:  /store/california/                        ← Сохраняется
EN:  /en/store/california/                     ← Новый
```

---

### Шаг 2: Добавить hreflang теги в templates/base.html (ПРАВИЛЬНО)

**Добавить в `<head>` после мета-тегов:**

```django
{% load i18n %}
{% get_current_language as CURRENT_LANG %}
{% get_available_languages as LANGUAGES %}

<!-- SEO: hreflang теги для мультиязычности -->
{% for lang_code, lang_name in LANGUAGES %}
    {% language lang_code %}
        <link rel="alternate" hreflang="{{ lang_code }}" href="{{ request.scheme }}://{{ request.get_host }}{% translate_url lang_code %}">
    {% endlanguage %}
{% endfor %}
<!-- x-default указывает на испанскую версию (дефолт) -->
{% language 'es' %}
    <link rel="alternate" hreflang="x-default" href="{{ request.scheme }}://{{ request.get_host }}{% translate_url 'es' %}">
{% endlanguage %}

<!-- SEO: Canonical URL (без query-параметров) -->
<link rel="canonical" href="{{ request.scheme }}://{{ request.get_host }}{{ request.path }}">

<!-- SEO: OpenGraph -->
<meta property="og:url" content="{{ request.build_absolute_uri }}">
<meta property="og:locale" content="{% if CURRENT_LANG == 'es' %}es_ES{% else %}en_US{% endif %}">
<meta property="og:locale:alternate" content="{% if CURRENT_LANG == 'es' %}en_US{% else %}es_ES{% endif %}">
```

**Что это дает:**

На странице `/strain/northern-lights/` (ES):
```html
<link rel="alternate" hreflang="es" href="https://cannamente.com/strain/northern-lights/">
<link rel="alternate" hreflang="en" href="https://cannamente.com/en/strain/northern-lights/">
<link rel="alternate" hreflang="x-default" href="https://cannamente.com/strain/northern-lights/">
<link rel="canonical" href="https://cannamente.com/strain/northern-lights/">
```

На странице `/en/strain/northern-lights/` (EN):
```html
<link rel="alternate" hreflang="es" href="https://cannamente.com/strain/northern-lights/">
<link rel="alternate" hreflang="en" href="https://cannamente.com/en/strain/northern-lights/">
<link rel="alternate" hreflang="x-default" href="https://cannamente.com/strain/northern-lights/">
<link rel="canonical" href="https://cannamente.com/en/strain/northern-lights/">
```

---

### Шаг 3: Обновить Language Switcher в base.html (ПРАВИЛЬНО)

**Проблема текущего switcher:**
```html
<!-- Текущий switcher меняет только сессию! -->
<form action="{% url 'set_language' %}" method="post" class="language-switcher">
    {% csrf_token %}
    <input name="next" type="hidden" value="{{ request.path }}">
    <select name="language" onchange="this.form.submit()">
        ...
    </select>
</form>
```

Это оставляет пользователя на том же URL, просто меняет язык контента в сессии.

**Правильный switcher (меняет URL через translate_url):**

```django
{% load i18n %}
{% get_current_language as CURRENT_LANG %}
{% get_available_languages as LANGUAGES %}

<!-- Language Switcher -->
<div class="language-switcher">
    {% for lang_code, lang_name in LANGUAGES %}
        {% if lang_code != CURRENT_LANG %}
            {% language lang_code %}
                <a href="{% translate_url lang_code %}" class="language-link">
                    {% if lang_code == 'en' %}🇬🇧 EN{% elif lang_code == 'es' %}🇪🇸 ES{% endif %}
                </a>
            {% endlanguage %}
        {% else %}
            {# Текущий язык (не кликабельный) #}
            <span class="language-current">
                {% if lang_code == 'en' %}🇬🇧 EN{% elif lang_code == 'es' %}🇪🇸 ES{% endif %}
            </span>
        {% endif %}
    {% endfor %}
</div>
```

**Преимущества `translate_url`:**
- ✅ Автоматически добавляет/убирает `/en/` префикс
- ✅ Работает с любыми языками
- ✅ Не ломается при изменении URL-структуры
- ✅ Сохраняет query-параметры (если нужно)

---

### Шаг 4: Обновить Sitemap с hreflang в XML (ПРАВИЛЬНО)

**Проблемы старого подхода:**
1. Генерация путей строками (f'/en/strain/{slug}/') - хрупко
2. Нет hreflang в XML (только в HTML)
3. Отдельные классы для каждого языка - дублирование кода

**Правильное решение:** Класс I18nSitemap с двунаправленными hreflang

```python
# canna/sitemaps.py
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.utils import translation
from apps.strains.models import Strain, Article


class I18nSitemap(Sitemap):
    """
    Base sitemap with hreflang support in XML.

    Generates entries for all languages with bidirectional hreflang links.
    """
    languages = ['es', 'en']
    protocol = 'https'

    def get_urls(self, page=1, site=None, protocol=None):
        """
        Override to add hreflang alternates to each URL.

        Returns URLs with structure:
        {
            'location': 'https://cannamente.com/strain/northern-lights/',
            'lastmod': datetime(...),
            'alternates': [
                {'language': 'es', 'location': 'https://...'},
                {'language': 'en', 'location': 'https://...'},
            ]
        }
        """
        urls = []
        latest_lastmod = None
        all_items_lastmod = True

        # Get all items once
        items = self.items()

        for item in items:
            # Generate URLs for all languages
            loc_alternates = []
            primary_url = None

            for lang in self.languages:
                with translation.override(lang):
                    # Use reverse() in language context
                    loc = self._location(item, force_lang=lang)
                    loc_full = self._get_full_url(loc)

                    loc_alternates.append({
                        'language': lang,
                        'location': loc_full,
                    })

                    # Primary URL is Spanish (default)
                    if lang == 'es':
                        primary_url = loc_full

            # Get lastmod
            lastmod = self.lastmod(item)
            if all_items_lastmod:
                all_items_lastmod = lastmod is not None
                if lastmod and (latest_lastmod is None or lastmod > latest_lastmod):
                    latest_lastmod = lastmod

            # Build URL entry
            url_entry = {
                'item': item,
                'location': primary_url,
                'lastmod': lastmod,
                'changefreq': self.changefreq,
                'priority': str(self.priority if self.priority is not None else ''),
                'alternates': loc_alternates,
            }

            urls.append(url_entry)

        return urls

    def _location(self, obj, force_lang=None):
        """Override in subclass to generate URL via reverse()"""
        raise NotImplementedError('Subclasses must implement _location()')

    def _get_full_url(self, path):
        """Convert path to full URL"""
        return f'{self.protocol}://cannamente.com{path}'


class StrainSitemap(I18nSitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return Strain.objects.filter(active=True).order_by('-id')

    def lastmod(self, obj):
        return obj.updated_at if hasattr(obj, 'updated_at') else None

    def _location(self, obj, force_lang=None):
        # reverse() автоматически добавит /en/ если нужно
        return reverse('strain_detail', kwargs={'slug': obj.slug})


class ArticleSitemap(I18nSitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Article.objects.all().order_by('-id')

    def lastmod(self, obj):
        return obj.updated_at if hasattr(obj, 'updated_at') else None

    def _location(self, obj, force_lang=None):
        return reverse('article_detail', kwargs={'slug': obj.slug})


class TerpeneSitemap(I18nSitemap):
    changefreq = "monthly"
    priority = 0.7

    def items(self):
        from apps.strains.models import Terpene
        return Terpene.objects.all().order_by('name')

    def _location(self, obj, force_lang=None):
        return reverse('terpene_detail', kwargs={'slug': obj.slug})
```

**Создать кастомный шаблон sitemap с hreflang:**

```xml
<!-- templates/sitemap.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:xhtml="http://www.w3.org/1999/xhtml">
{% spaceless %}
{% for url in urlset %}
  <url>
    <loc>{{ url.location }}</loc>
    {% if url.lastmod %}<lastmod>{{ url.lastmod|date:"Y-m-d" }}</lastmod>{% endif %}
    {% if url.changefreq %}<changefreq>{{ url.changefreq }}</changefreq>{% endif %}
    {% if url.priority %}<priority>{{ url.priority }}</priority>{% endif %}
    {% if url.alternates %}
      {% for alternate in url.alternates %}
    <xhtml:link rel="alternate" hreflang="{{ alternate.language }}" href="{{ alternate.location }}" />
      {% endfor %}
    <xhtml:link rel="alternate" hreflang="x-default" href="{{ url.alternates.0.location }}" />
    {% endif %}
  </url>
{% endfor %}
{% endspaceless %}
</urlset>
```

**Обновить canna/urls.py:**

```python
from django.contrib.sitemaps.views import sitemap
from canna.sitemaps import StrainSitemap, ArticleSitemap, TerpeneSitemap

sitemaps = {
    'strains': StrainSitemap(),
    'articles': ArticleSitemap(),
    'terpenes': TerpeneSitemap(),
}

urlpatterns += i18n_patterns(
    # ...
    path('sitemap.xml', sitemap, {
        'sitemaps': sitemaps,
        'template_name': 'sitemap.xml'  # Кастомный шаблон с hreflang
    }, name='django.contrib.sitemaps.views.sitemap'),
    prefix_default_language=False
)
```

**Результат в sitemap.xml:**

```xml
<url>
  <loc>https://cannamente.com/strain/northern-lights/</loc>
  <lastmod>2025-10-10</lastmod>
  <changefreq>weekly</changefreq>
  <priority>0.9</priority>
  <xhtml:link rel="alternate" hreflang="es" href="https://cannamente.com/strain/northern-lights/" />
  <xhtml:link rel="alternate" hreflang="en" href="https://cannamente.com/en/strain/northern-lights/" />
  <xhtml:link rel="alternate" hreflang="x-default" href="https://cannamente.com/strain/northern-lights/" />
</url>
```

---

### Шаг 5: Обновить настройки (опционально)

**canna/settings.py:**

```python
# Язык по умолчанию (без префикса в URL)
LANGUAGE_CODE = 'es'

LANGUAGES = [
    ('es', 'Español'),  # Default - без префикса
    ('en', 'English'),  # С префиксом /en/
]

# Для django-modeltranslation
MODELTRANSLATION_DEFAULT_LANGUAGE = 'es'  # Изменить с 'en' на 'es'
MODELTRANSLATION_LANGUAGES = ('es', 'en')  # Порядок: ES первый
MODELTRANSLATION_FALLBACK_LANGUAGES = ('es',)  # Fallback на испанский
```

---

## Тестирование

### 1. Проверить URL вручную

```bash
# Запустить сервер
docker-compose up

# Испанские URL (должны работать БЕЗ изменений)
curl http://localhost:8000/
curl http://localhost:8000/strains/
curl http://localhost:8000/strain/northern-lights/
curl http://localhost:8000/articles/

# Английские URL (новые, с префиксом /en/)
curl http://localhost:8000/en/
curl http://localhost:8000/en/strains/
curl http://localhost:8000/en/strain/northern-lights/
curl http://localhost:8000/en/articles/
```

### 2. Проверить hreflang теги

```bash
curl http://localhost:8000/strain/northern-lights/ | grep hreflang
# Должно вывести:
# <link rel="alternate" hreflang="es" href="https://cannamente.com/strain/northern-lights/">
# <link rel="alternate" hreflang="en" href="https://cannamente.com/en/strain/northern-lights/">
# <link rel="alternate" hreflang="x-default" href="https://cannamente.com/strain/northern-lights/">
```

### 3. Проверить sitemap

```bash
curl http://localhost:8000/sitemap.xml
# Должен содержать:
# - strains-es: /strain/northern-lights/
# - strains-en: /en/strain/northern-lights/
# - articles-es: /articles/some-article/
# - articles-en: /en/articles/some-article/
```

### 4. Проверить language switcher

1. Открыть `/strain/northern-lights/` (испанский)
2. Кликнуть "🇬🇧 EN"
3. Должно перенаправить на `/en/strain/northern-lights/` (английский)
4. Кликнуть "🇪🇸 ES"
5. Должно перенаправить на `/strain/northern-lights/` (испанский)

---

## Google Search Console

### После деплоя:

1. **Добавить новую версию сайта:**
   - Search Console → Добавить свойство → `https://cannamente.com/en/`

2. **Проверить hreflang:**
   - Search Console → International Targeting → Language
   - Должны быть видны связи между ES и EN версиями

3. **Отправить обновленный sitemap:**
   - Search Console → Sitemaps → Добавить/Протестировать sitemap
   - URL: `https://cannamente.com/sitemap.xml`

4. **Мониторинг:**
   - Search Console → Coverage → Проверить индексацию новых /en/ URL
   - Search Console → Performance → Фильтр по языку

---

## Ожидаемые результаты

### Через 1-2 недели:
- ✅ Google начнет индексировать английские URL с `/en/`
- ✅ Испанские URL останутся без изменений (сохранен SEO)
- ✅ В поисковой выдаче будут показываться правильные версии по языку пользователя

### Через 1-2 месяца:
- ✅ Полная индексация обеих языковых версий
- ✅ Органический трафик из англоязычных стран
- ✅ Улучшение позиций в англоязычной выдаче

---

## Альтернативное решение (НЕ рекомендуется)

### Вариант 2: Оба языка с префиксами + 301 редиректы

```
/es/strain/northern-lights/  → Испанский (НОВЫЙ URL)
/en/strain/northern-lights/  → Английский (НОВЫЙ URL)
/strain/northern-lights/     → 301 Redirect → /es/strain/northern-lights/
```

**Преимущества:**
- ✅ Чистая структура (оба с префиксами)
- ✅ Легко масштабировать (добавить FR, DE, etc.)

**Недостатки:**
- ❌ Все испанские URL изменятся!
- ❌ Потребуется настройка 301 редиректов
- ❌ Google должен переиндексировать ВСЕ страницы
- ❌ Временная потеря SEO позиций (1-2 месяца)
- ❌ Потеря внешних ссылок (если не настроить редиректы)

---

## Рекомендации

### ✅ Рекомендуется (Вариант 1):
- Испанский БЕЗ префикса (сохранить текущие URL)
- Английский С префиксом `/en/` (новые URL)
- `prefix_default_language=False` в urls.py

### ❌ НЕ рекомендуется (Вариант 2):
- Оба языка с префиксами
- Требует 301 редиректы
- Риск потери SEO

---

## Контрольный чеклист перед деплоем (ОБНОВЛЕН)

### Критические требования ✅

**URL структура:**
- [ ] Обновлен `canna/urls.py` с `i18n_patterns(prefix_default_language=False)`
- [ ] Испанские URL БЕЗ префикса: `/strain/...` ← Сохранены!
- [ ] Английские URL С префиксом: `/en/strain/...` ← Новые

**HTML мета-теги:**
- [ ] hreflang через `{% translate_url %}` (НЕ через slice!)
- [ ] Canonical без query-параметров
- [ ] OpenGraph с og:locale и og:locale:alternate
- [ ] HTML lang="{{ LANGUAGE_CODE }}"

**Language Switcher:**
- [ ] Использует `{% translate_url %}` для изменения URL
- [ ] НЕ использует form с set_language (старый метод)

**Sitemap:**
- [ ] Создан I18nSitemap с hreflang В XML
- [ ] Использует reverse() с translation.override
- [ ] xmlns:xhtml в шаблоне sitemap.xml
- [ ] Двунаправленные <xhtml:link> для ES↔EN

**Middleware:**
- [ ] Создан LanguageUrlRedirectMiddleware
- [ ] Добавлен в MIDDLEWARE после LocaleMiddleware
- [ ] Редиректит EN-сессию на ES-пути → /en/...

**Structured Data:**
- [ ] JSON-LD содержит "inLanguage": current_lang
- [ ] "@id" уникален для каждого языка

**Тесты:**
- [ ] test_spanish_urls_unchanged
- [ ] test_english_urls_have_prefix
- [ ] test_hreflang_bidirectional
- [ ] test_canonical_correct
- [ ] test_sitemap_has_both_languages
- [ ] test_no_vary_accept_language

**Безопасность:**
- [ ] Backup базы данных создан
- [ ] План отката готов
- [ ] Staging тестирование пройдено

### Проверка вручную 🔍

**1. Испанские URL (должны работать БЕЗ изменений):**
```bash
curl https://cannamente.com/
curl https://cannamente.com/strains/
curl https://cannamente.com/strain/northern-lights/
curl https://cannamente.com/articles/
```

**2. Английские URL (новые, с /en/):**
```bash
curl https://cannamente.com/en/
curl https://cannamente.com/en/strains/
curl https://cannamente.com/en/strain/northern-lights/
curl https://cannamente.com/en/articles/
```

**3. hreflang в HTML:**
```bash
curl https://cannamente.com/strain/northern-lights/ | grep 'hreflang'
# Должно быть: es, en, x-default
```

**4. hreflang в sitemap.xml:**
```bash
curl https://cannamente.com/sitemap.xml | grep 'xhtml:link'
# Должны быть <xhtml:link rel="alternate" hreflang="es" ...>
```

**5. Language switcher:**
- Открыть `/strain/northern-lights/` (ES)
- Кликнуть "EN" → должно перейти на `/en/strain/northern-lights/`
- Кликнуть "ES" → должно вернуться на `/strain/northern-lights/`

**6. Canonical:**
```bash
curl 'https://cannamente.com/strain/northern-lights/?utm_source=test' | grep 'canonical'
# НЕ должен содержать utm_source
```

### После деплоя 🚀

**Google Search Console:**
- [ ] Добавлено свойство для /en/ (или Domain property)
- [ ] Отправлен обновленный sitemap.xml
- [ ] Проверка hreflang через International Targeting

**Мониторинг:**
- [ ] Coverage: обе языковые версии индексируются
- [ ] Performance: фильтр по стране/языку
- [ ] Errors: нет ошибок hreflang

**robots.txt:**
- [ ] Добавлен `Sitemap: https://cannamente.com/sitemap.xml`

---

## Дополнительные улучшения (опционально)

### 1. Structured Data (JSON-LD) с языком

Убедиться что JSON-LD содержит правильный язык:

```python
# В strain_detail view
{
    "@context": "https://schema.org",
    "@type": "Product",
    "name": strain.name,
    "description": strain.description,  # Автоматически берет правильный язык
    "inLanguage": get_language(),  # 'es' или 'en'
    ...
}
```

### 2. OpenGraph и Twitter Cards с языком

```html
<meta property="og:locale" content="{% if CURRENT_LANG == 'es' %}es_ES{% else %}en_US{% endif %}">
<meta property="og:locale:alternate" content="{% if CURRENT_LANG == 'es' %}en_US{% else %}es_ES{% endif %}">
```

### 3. HTML lang attribute (уже есть в base.html)

```html
<html lang="{{ LANGUAGE_CODE }}">  <!-- ✅ Уже реализовано -->
```

---

**Версия:** 1.0
**Дата:** 2025-10-10
**Автор:** Claude (AI Translation Implementation)
