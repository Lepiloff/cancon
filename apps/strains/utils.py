from django.db.models import Count, Q

from apps.strains.models import Strain


def is_ajax_request(request):
    """Check if the request is an AJAX request."""
    return ('HTTP_X_REQUESTED_WITH' in request.META
            and request.META['HTTP_X_REQUESTED_WITH'] == 'XMLHttpRequest')


def get_related_strains(strain):
    """Get strains related to a particular strain."""
    feelings_ids = strain.feelings.values_list('id', flat=True)

    related_strains = Strain.objects.filter(
        category=strain.category, active=True
    ).exclude(
        id=strain.id
    ).annotate(
        common_feelings_count=Count(
            'feelings',
            filter=Q(feelings__id__in=feelings_ids)
        )
    ).order_by('-common_feelings_count')

    # Если похожих сортов меньше 8, то докидываем до 8 по категории
    if related_strains.count() < 8:
        additional_strains = Strain.objects.filter(
            category=strain.category, active=True
        ).exclude(
            id__in=related_strains.values_list('id', flat=True)
        ).exclude(
            id=strain.id
        )[:8 - related_strains.count()]
        related_strains = list(related_strains) + list(additional_strains)

    return related_strains[:8]


def get_filtered_strains(form):
    strains = Strain.objects.filter(active=True)

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
    return strains.distinct().order_by('name')
