from django.db.models import Count, Q
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.urls import reverse

from apps.strains.localizations import (
    feelings_translation,
    helps_with_translation,
    flavors_translation,
)
from apps.strains.forms import StrainFilterForm
from apps.strains.models import Article, Strain


def main_page(request):
    strains = Strain.objects.filter(active=True, main=True).order_by('-rating')[:8]
    context = {
        'strains': strains,
    }
    return render(request, 'main.html', context)


def strain_detail(request, slug):
    strain = get_object_or_404(Strain, slug=slug, active=True)

    # Получаем сорта с той же категорией и схожими эффектами
    related_strains = Strain.objects.filter(
        category=strain.category, active=True).exclude(
        id=strain.id).annotate(
        common_feelings_count=Count('feelings', filter=Q(
            feelings__in=strain.feelings.all()))).order_by('-common_feelings_count')

    # Если похожих сортов меньше 8, то докидываем до 8 по категории
    if related_strains.count() < 8:
        additional_strains = Strain.objects.filter(
            category=strain.category, active=True).exclude(
            id__in=related_strains.values_list('id', flat=True)).exclude(
            id=strain.id)[:8 - related_strains.count()]
        related_strains = list(related_strains) + list(additional_strains)

    context = {
        'strain': strain,
        'strains': related_strains[:8],  # Ограничиваем до 8, на случай если набралось больше
    }

    return render(request, 'strain.html', context)


def strain_list(request):
    page = request.GET.get('page', 1)
    offset = (int(page) - 1) * 20

    # Создание изменяемого QueryDict объекта
    mutable_params = request.GET.copy()

    for key in mutable_params.keys():
        if ',' in mutable_params[key]:
            mutable_params.setlist(key, mutable_params[key].split(','))

    form = StrainFilterForm(mutable_params or None)
    strains = Strain.objects.filter(active=True)

    # Проверяем, содержит ли запрос параметры, которые мы не ожидаем
    expected_params = ['category', 'thc', 'feelings', 'helps_with', 'flavors', 'page']
    if any(param not in expected_params for param in mutable_params):
        return render(request, 'strains.html', {'form': form, 'no_matches': True})

    if form.is_valid():
        if form.cleaned_data['category']:
            strains = strains.filter(category__in=form.cleaned_data['category'])

        if form.cleaned_data['thc']:
            thc_choices = form.cleaned_data['thc']
            thc_conditions = Q()
            if 'sin thc' in thc_choices:
                thc_conditions |= Q(thc=0)
            if 'bajo thc' in thc_choices:
                thc_conditions |= Q(thc__range=(1, 10))
            if 'medio thc' in thc_choices:
                thc_conditions |= Q(thc__range=(11, 20))
            if 'alto thc' in thc_choices:
                thc_conditions |= Q(thc__gt=20)
            strains = strains.filter(thc_conditions)

        if form.cleaned_data['feelings']:
            strains = strains.filter(feelings__in=form.cleaned_data['feelings'])

        if form.cleaned_data['helps_with']:
            strains = strains.filter(helps_with__in=form.cleaned_data['helps_with'])

        if form.cleaned_data['flavors']:
            strains = strains.filter(flavors__in=form.cleaned_data['flavors'])

    # Проверка, есть ли совпадения
    no_matches = not strains.exists()

    strains = strains.order_by('name')[offset:offset + 20]

    if 'HTTP_X_REQUESTED_WITH' in request.META and request.META['HTTP_X_REQUESTED_WITH'] == 'XMLHttpRequest':
        if not strains:
            return HttpResponse(status=204)
        html_strains = render_to_string('strain_items.html', {'strains': strains})
        return HttpResponse(html_strains)

    return render(request, 'strains.html', {
        'strains': strains,
        'form': form,
        'no_matches': no_matches,
        'feelings_translation': feelings_translation,
        'helps_with_translation': helps_with_translation,
        'flavors_translation': flavors_translation,
    }
                  )


def search(request):
    query = request.GET.get('q')
    if query:
        results = Strain.objects.filter(name__icontains=query)
        if 'HTTP_X_REQUESTED_WITH' in request.META and request.META['HTTP_X_REQUESTED_WITH'] == 'XMLHttpRequest':
            links = [{'name': strain.name, 'url': reverse('strain_detail', args=[strain.slug])} for strain in results]
            html = render_to_string('modal_body.html', {'links': links})
            return HttpResponse(html)
        else:
            return redirect('/')
    else:
        return HttpResponse("No query provided")


def article_list(request):
    category = request.GET.get('category')
    articles = Article.objects.all()

    if category:
        articles = articles.filter(category__name=category)

    if 'HTTP_X_REQUESTED_WITH' in request.META and request.META['HTTP_X_REQUESTED_WITH'] == 'XMLHttpRequest':
        html_articles = render_to_string('articles.html', {'articles': articles})
        return HttpResponse(html_articles)

    return render(request, 'articles.html', {'articles': articles})


def article_detail(request, slug):
    article = get_object_or_404(Article, slug=slug)
    image = article.images.filter(is_preview=False).first()

    return render(request, 'article_detail.html', {'article': article, 'image': image})


