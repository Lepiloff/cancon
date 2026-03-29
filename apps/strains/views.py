import re

from bs4 import BeautifulSoup

from django.db.models import Q, Max, Prefetch
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.urls import reverse

from apps.strains.forms import StrainFilterForm
from apps.strains.models import Article, ArticleCategory, ArticleImage, Strain, Terpene
from apps.strains.utils import get_related_strains, get_filtered_strains, is_ajax_request


def _extract_headings(html_content):
    """Extract h3 headings from HTML, respecting current language content."""
    if not html_content:
        return []
    soup = BeautifulSoup(html_content, 'html.parser')
    return [
        {'id': h.get('id', ''), 'text': h.get_text()}
        for h in soup.find_all('h3')
        if h.get('id')
    ]


def custom_page_not_found_view(request, exception):
    response = render(request, '404.html', {})
    response.status_code = 404
    return response


def main_page(request):
    strains = Strain.objects.filter(active=True, main=True).order_by('-rating')[:8]
    articles = Article.objects.exclude(category__name__in=['TOP 10', 'Terpenes']).order_by('-created_at')[:6]
    context = {
        'strains': strains,
        'articles': articles,
    }
    return render(request, 'main_v2.html', context)


def _get_terpene_article_slugs(terpenes):
    """Build a dict mapping Terpene.id -> Article.slug for terpene detail links."""
    if not terpenes:
        return {}
    slugs = {}
    for terpene in terpenes:
        es_prefix = TERPENE_EN_TO_ES.get(terpene.name.lower())
        if es_prefix:
            article_slug = Article.objects.filter(
                category__name='Terpenes',
                slug__startswith=es_prefix,
            ).values_list('slug', flat=True).first()
            if article_slug:
                slugs[terpene.id] = article_slug
    return slugs


def strain_detail(request, slug):
    strain = get_object_or_404(
        Strain.objects.prefetch_related('feelings', 'negatives', 'flavors', 'helps_with',
                                        'dominant_terpene', 'other_terpenes', 'parents'), slug=slug,
        active=True)
    related_strains = get_related_strains(strain)

    # Max cannabinoid values for proportional bar rendering
    cann_max = Strain.objects.filter(active=True).aggregate(
        max_thc=Max('thc'), max_cbd=Max('cbd'), max_cbg=Max('cbg')
    )

    # Build terpene -> article slug mapping for clickable links
    all_terpenes = list(filter(None, [strain.dominant_terpene])) + list(strain.other_terpenes.all())
    terpene_slugs = _get_terpene_article_slugs(all_terpenes)

    # Attach article slugs to terpene objects for template use
    if strain.dominant_terpene:
        strain.dominant_terpene.article_slug = terpene_slugs.get(strain.dominant_terpene.id)
    for t in strain.other_terpenes.all():
        t.article_slug = terpene_slugs.get(t.id)

    context = {
        'strain': strain,
        'strains': related_strains,
        'max_thc': cann_max['max_thc'] or 1,
        'max_cbd': cann_max['max_cbd'] or 1,
        'max_cbg': cann_max['max_cbg'] or 1,
    }

    return render(request, 'strain_modern_v2.html', context)


def strain_list(request):
    try:
        page = int(request.GET.get('page', 1))
    except (ValueError, TypeError):
        page = 1
    offset = (page - 1) * 20

    mutable_params = request.GET.copy()
    for key in mutable_params.keys():
        if ',' in mutable_params[key]:
            mutable_params.setlist(key, mutable_params[key].split(','))

    form = StrainFilterForm(mutable_params or None)

    expected_params = ['category', 'thc', 'feelings', 'helps_with', 'flavors', 'page']
    if any(param not in expected_params for param in mutable_params):
        return render(
            request, 'strains_v2.html', {'form': form, 'no_matches': True}
        )

    if form.is_valid():
        strains = get_filtered_strains(form)
    else:
        strains = Strain.objects.filter(active=True).order_by('name')

    no_matches = not strains.exists()

    strains = strains[offset:offset + 20]

    if is_ajax_request(request):
        if not strains:
            return HttpResponse(status=204)
        html_strains = render_to_string(
            'strain_items_v2.html', {'strains': strains}
        )
        return HttpResponse(html_strains)

    return render(request, 'strains_v2.html', {
        'strains': strains,
        'form': form,
        'no_matches': no_matches,
    })


def _extract_featured_strains(html_content):
    """Extract strain slugs from links in article HTML, preserving order of appearance."""
    if not html_content:
        return []
    soup = BeautifulSoup(html_content, 'html.parser')
    seen = set()
    slugs = []
    for a in soup.find_all('a', href=True):
        match = re.search(r'/strain/([\w-]+)/?', a['href'])
        if match:
            slug = match.group(1)
            if slug not in seen:
                seen.add(slug)
                slugs.append(slug)
    return slugs


def _find_strain_slug_in_element(el, strains_by_slug):
    """Find the first matching strain slug from links in an element."""
    for a in el.find_all('a', href=True):
        match = re.search(r'/strain/([\w-]+)/?', a['href'])
        if match and match.group(1) in strains_by_slug:
            return match.group(1)
    return None


def _parse_top10_content(html_content, strains_by_slug):
    """Parse Top 10 article HTML into intro, strain sections, and outro.

    Handles varied TinyMCE structures: some articles have one <p> per strain
    with an inline link, others have <img> + <h3> + <p> groups per strain.
    Deduplicates by slug — only the first occurrence creates a section.
    Standalone images and headings for strains are skipped (card replaces them).
    """
    if not html_content:
        return [], [], []

    soup = BeautifulSoup(html_content, 'html.parser')
    intro = []
    strain_sections = []
    outro = []
    seen_slugs = set()
    found_first_strain = False

    for el in soup.children:
        # Skip whitespace text nodes
        if not hasattr(el, 'name') or el.name is None:
            continue

        slug = _find_strain_slug_in_element(el, strains_by_slug)

        if slug:
            found_first_strain = True
            if slug not in seen_slugs:
                seen_slugs.add(slug)
                # Extract description: inline <p> with text, or nested <p> inside a container
                description = ''
                if el.name == 'p' and len(el.get_text(strip=True)) > 30:
                    description = str(el)
                elif el.name == 'div':
                    # Container div (e.g. TinyMCE strain-container) — find <p> inside
                    for p in el.find_all('p', recursive=True):
                        if len(p.get_text(strip=True)) > 30 and not p.find('a', href=True):
                            description = str(p)
                            break
                strain_sections.append({
                    'strain': strains_by_slug[slug],
                    'description': description,
                })
            else:
                # Duplicate slug — but if it's a <p> with real text, use as description
                if el.name == 'p' and len(el.get_text(strip=True)) > 30:
                    for section in strain_sections:
                        if section['strain'].slug == slug and not section['description']:
                            section['description'] = str(el)
                            break
        elif not found_first_strain:
            # Before any strain — intro content
            if el.name in ('p', 'h2', 'h3', 'h4', 'ul', 'ol', 'blockquote'):
                intro.append(str(el))
        elif strain_sections and not strain_sections[-1]['description'] and el.name == 'p':
            # Plain <p> right after a strain entry without description yet — it IS the description
            strain_sections[-1]['description'] = str(el)
        else:
            # After strains — outro text (skip images)
            if el.name in ('p', 'h2', 'h3', 'h4', 'ul', 'ol', 'blockquote'):
                text = el.get_text(strip=True)
                if text:
                    outro.append(str(el))

    return intro, strain_sections, outro


def _get_related_articles(article, limit=3, min_same_category=2):
    """Get related articles for the detail page.

    Finds articles sharing the same category as the current article,
    excluding Terpenes category. If fewer than min_same_category are found,
    pads with recent articles from any non-Terpenes category.
    """
    preview_image_prefetch = Prefetch(
        'images',
        queryset=ArticleImage.objects.filter(is_preview=True),
        to_attr='preview_images',
    )
    category_ids = article.category.exclude(name='Terpenes').values_list('id', flat=True)

    same_category = list(
        Article.objects.filter(category__id__in=category_ids)
        .exclude(pk=article.pk)
        .order_by('-created_at')
        .prefetch_related(preview_image_prefetch, 'category')
        .distinct()[:limit]
    )

    if len(same_category) >= min_same_category:
        return same_category

    existing_ids = {a.pk for a in same_category} | {article.pk}
    remaining = limit - len(same_category)
    filler = list(
        Article.objects.exclude(pk__in=existing_ids)
        .exclude(category__name='Terpenes')
        .order_by('-created_at')
        .prefetch_related(preview_image_prefetch, 'category')
        .distinct()[:remaining]
    )

    return same_category + filler


def article_detail(request, slug):
    article = get_object_or_404(Article, slug=slug)
    image = article.images.filter(is_preview=False).first()
    headings = _extract_headings(article.text_content)

    is_top10 = article.category.filter(name='TOP 10').exists()

    strain_slugs = _extract_featured_strains(article.text_content)
    strains_by_slug = {
        s.slug: s
        for s in Strain.objects.filter(slug__in=strain_slugs).prefetch_related('feelings', 'flavors')
    }
    featured_strains = [strains_by_slug[s] for s in strain_slugs if s in strains_by_slug]

    related_articles = [] if is_top10 else _get_related_articles(article)

    context = {
        'article': article,
        'image': image,
        'headings': headings,
        'featured_strains': featured_strains,
        'is_top10': is_top10,
        'related_articles': related_articles,
    }

    if is_top10:
        intro, strain_sections, outro = _parse_top10_content(
            article.text_content, strains_by_slug
        )
        context['intro_html'] = '\n'.join(intro)
        context['strain_sections'] = strain_sections
        context['outro_html'] = '\n'.join(outro)

    return render(request, 'article_detail_v2.html', context)


def article_list(request):
    category = request.GET.get('category')
    articles = Article.objects.exclude(
        category__name__in=['TOP 10', 'Terpenes']
    ).order_by('-created_at').prefetch_related('images', 'category')

    if category:
        articles = articles.filter(category__name=category)

    main_image = None
    if articles:
        main_image = articles[0].images.filter(is_preview=False).first()

    categories = ArticleCategory.objects.exclude(
        name__in=['TOP 10', 'Terpenes']
    )

    context = {
        'articles': articles,
        'main_image': main_image,
        'categories': categories,
        'current_category': category,
    }

    if is_ajax_request(request):
        html_articles = render_to_string(
            'articles_v2.html', context
        )
        return HttpResponse(html_articles)

    return render(request, 'articles_v2.html', context)


def search(request):
    query = request.GET.get('q')
    if query:
        results = Strain.objects.filter(
            Q(name__icontains=query) |
            Q(alternative_names__name__icontains=query)
        ).distinct()
        links = [
            {'name': strain.name, 'url': reverse('strain_detail', args=[strain.slug])}
            for strain in results
        ]

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            html = render_to_string('modal_body.html', {'links': links})
            return HttpResponse(html)
        else:
            return redirect('/')
    else:
        return HttpResponse("No query provided")


def terpene_list(request):
    terpenes = Article.objects.filter(category__name='Terpenes').prefetch_related('images')

    terpenes_with_images = []
    for terpene in terpenes:
        preview_image = terpene.images.filter(is_preview=True).first()
        terpenes_with_images.append({
            'terpene': terpene,
            'preview_image': preview_image,
            'title': terpene.title,
            'slug': terpene.slug,
        })

    return render(request, 'terpene_list_v2.html', {'terpenes_with_images': terpenes_with_images})


# Mapping from Spanish terpene name prefixes (as they appear in Article titles)
# to English terpene name prefixes (as stored in Terpene.name).
TERPENE_ES_TO_EN = {
    'mirceno': 'myrcene',
    'cariofileno': 'caryophyllene',
    'limoneno': 'limonene',
    'linalool': 'linalool',
    'pineno': 'pinene',
    'humuleno': 'humulene',
    'terpinoleno': 'terpinolene',
    'ocimeno': 'ocimene',
}
TERPENE_EN_TO_ES = {v: k for k, v in TERPENE_ES_TO_EN.items()}


def _find_terpene_for_article(article: Article):
    """Match an Article (terpene page) to its corresponding Terpene model entry.

    Strategy: extract the first word from the article title, map it from Spanish
    to English using TERPENE_ES_TO_EN, then find the Terpene whose name contains
    that English keyword (case-insensitive).
    """
    first_word = article.title.split(':')[0].split()[0].lower() if article.title else ''
    en_keyword = TERPENE_ES_TO_EN.get(first_word)
    if not en_keyword:
        return None
    return Terpene.objects.filter(name__icontains=en_keyword).first()


def _get_related_terpenes(terpene_article, limit=3):
    """Get other terpene articles for the related section."""
    preview_image_prefetch = Prefetch(
        'images',
        queryset=ArticleImage.objects.filter(is_preview=True),
        to_attr='preview_images',
    )
    return list(
        Article.objects.filter(category__name='Terpenes')
        .exclude(pk=terpene_article.pk)
        .order_by('-created_at')
        .prefetch_related(preview_image_prefetch)
        .distinct()[:limit]
    )


def terpene_detail(request, slug):
    terpene = get_object_or_404(Article, slug=slug, category__name='Terpenes')
    image = terpene.images.filter(is_preview=False).first()
    headings = _extract_headings(terpene.text_content)

    terpene_strains = []
    matched_terpene = _find_terpene_for_article(terpene)
    if matched_terpene:
        terpene_strains = (
            Strain.objects.filter(
                Q(dominant_terpene=matched_terpene) | Q(other_terpenes=matched_terpene),
                active=True,
            )
            .distinct()
            .order_by('-rating')[:8]
        )

    related_terpenes = _get_related_terpenes(terpene)

    return render(
        request,
        'terpene_detail_v2.html',
        {
            'terpene': terpene,
            'image': image,
            'headings': headings,
            'terpene_strains': terpene_strains,
            'related_terpenes': related_terpenes,
        }
    )

