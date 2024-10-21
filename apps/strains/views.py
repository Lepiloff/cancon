from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.urls import reverse

from apps.strains.localizations import (
    feelings_translation,
    helps_with_translation,
    flavors_translation,
    negatives_translator,
    terpenes_translation,
)
from apps.strains.forms import StrainFilterForm
from apps.strains.models import Article, Strain
from apps.strains.utils import get_related_strains, get_filtered_strains, is_ajax_request


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
    return render(request, 'main.html', context)


def strain_detail(request, slug):
    strain = get_object_or_404(
        Strain.objects.prefetch_related('feelings', 'negatives', 'flavors', 'helps_with',
                                        'dominant_terpene', 'other_terpenes'), slug=slug,
        active=True)
    related_strains = get_related_strains(strain)

    context = {
        'strain': strain,
        'strains': related_strains,
        'feelings_translation': feelings_translation,
        'helps_with_translation': helps_with_translation,
        'flavors_translation': flavors_translation,
        'negatives_translator': negatives_translator,
        'terpenes_translation': terpenes_translation,
    }

    return render(request, 'strain.html', context)


def strain_list(request):
    page = request.GET.get('page', 1)
    offset = (int(page) - 1) * 20

    mutable_params = request.GET.copy()
    for key in mutable_params.keys():
        if ',' in mutable_params[key]:
            mutable_params.setlist(key, mutable_params[key].split(','))

    form = StrainFilterForm(mutable_params or None)

    expected_params = ['category', 'thc', 'feelings', 'helps_with', 'flavors', 'page']
    if any(param not in expected_params for param in mutable_params):
        return render(
            request, 'strains.html', {'form': form, 'no_matches': True}
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
            'strain_items.html', {'strains': strains}
        )
        return HttpResponse(html_strains)

    return render(request, 'strains.html', {
        'strains': strains,
        'form': form,
        'no_matches': no_matches,
        'feelings_translation': feelings_translation,
        'helps_with_translation': helps_with_translation,
        'flavors_translation': flavors_translation,
    })


def article_detail(request, slug):
    article = get_object_or_404(Article, slug=slug)
    image = article.images.filter(is_preview=False).first()
    headings = article.get_headings()
    return render(
        request,
        'article_detail.html',
        {'article': article, 'image': image, 'headings': headings}
    )


def article_list(request):
    category = request.GET.get('category')
    articles = Article.objects.exclude(category__name__in=['TOP 10', 'Terpenes']).order_by(
        '-created_at').prefetch_related('images')

    if category:
        articles = articles.filter(category__name=category)

    # Получаем первое изображение (не превью) только для первой статьи
    main_image = None
    if articles:
        main_image = articles[0].images.filter(is_preview=False).first()

    if is_ajax_request(request):
        html_articles = render_to_string(
            'articles.html',
            {'articles': articles, 'main_image': main_image}
        )
        return HttpResponse(html_articles)

    return render(request,
                  'articles.html',
                  {'articles': articles, 'main_image': main_image}
                  )


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

    return render(request, 'terpene_list.html', {'terpenes_with_images': terpenes_with_images})


def terpene_detail(request, slug):
    terpene = get_object_or_404(Article, slug=slug, category__name='Terpenes')
    image = terpene.images.filter(
        is_preview=False).first()
    headings = terpene.get_headings()
    return render(
        request,
        'terpene_detail.html',
        {
            'terpene': terpene,
            'image': image,
            'headings': headings
        }
    )


# SITEMAP #

def sitemap(request):
    strains = Strain.objects.filter(active=True)
    articles = Article.objects.all()

    context = {
        'strains': strains,
        'articles': articles,
    }

    return render(request, 'sitemap.html', context)

