import re

from bs4 import BeautifulSoup

from django.db.models import Q, Max
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.urls import reverse

from apps.strains.forms import StrainFilterForm
from apps.strains.models import Article, ArticleCategory, Strain
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


def _parse_top10_content(html_content, strains_by_slug):
    """Parse Top 10 article HTML into intro paragraphs, strain sections, and outro paragraphs."""
    if not html_content:
        return [], [], []

    soup = BeautifulSoup(html_content, 'html.parser')
    intro = []
    strain_sections = []
    outro = []
    found_first_strain = False
    last_strain_idx = -1

    elements = soup.find_all(['p', 'h2', 'h3', 'h4', 'ul', 'ol', 'blockquote', 'div'])

    for el in elements:
        link = el.find('a', href=True)
        strain_slug = None
        if link:
            match = re.search(r'/strain/([\w-]+)/?', link.get('href', ''))
            if match:
                strain_slug = match.group(1)

        if strain_slug and strain_slug in strains_by_slug:
            found_first_strain = True
            # Extract just the description text (without the strain name link text)
            description = str(el)
            strain_sections.append({
                'strain': strains_by_slug[strain_slug],
                'description': description,
            })
            last_strain_idx = len(strain_sections) - 1
        elif not found_first_strain:
            intro.append(str(el))
        else:
            # Check if this paragraph still belongs to a strain section
            # (no strain link = it's outro content)
            if last_strain_idx >= 0:
                outro.append(str(el))

    return intro, strain_sections, outro


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

    context = {
        'article': article,
        'image': image,
        'headings': headings,
        'featured_strains': featured_strains,
        'is_top10': is_top10,
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


def terpene_detail(request, slug):
    terpene = get_object_or_404(Article, slug=slug, category__name='Terpenes')
    image = terpene.images.filter(is_preview=False).first()
    headings = _extract_headings(terpene.text_content)
    return render(
        request,
        'terpene_detail_v2.html',
        {
            'terpene': terpene,
            'image': image,
            'headings': headings
        }
    )

