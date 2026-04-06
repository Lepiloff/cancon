import json

from django.core.paginator import Paginator
from django.http import Http404
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET, require_POST

from apps.strains.comment_moderation import moderate_strain_comment
from apps.strains.forms import StrainCommentForm
from apps.strains.models import FavoriteStrain, Strain, StrainComment
from apps.strains.views import STRAIN_COMMENTS_PAGE_SIZE


def _json_forbidden():
    return JsonResponse({'error': 'Authentication required'}, status=403)


@require_POST
def favorite_toggle(request):
    if not request.user.is_authenticated:
        return _json_forbidden()

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, TypeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    strain_id = data.get('strain_id')
    if not strain_id:
        return JsonResponse({'error': 'strain_id is required'}, status=400)

    try:
        strain = Strain.objects.get(pk=strain_id, active=True)
    except Strain.DoesNotExist:
        return JsonResponse({'error': 'Strain not found'}, status=404)

    favorite, created = FavoriteStrain.objects.get_or_create(
        user=request.user,
        strain=strain,
    )
    if created:
        status_value = 'added'
    else:
        favorite.delete()
        status_value = 'removed'

    return JsonResponse({
        'status': status_value,
        'strain_id': strain.id,
    })


@require_GET
def favorite_status(request):
    if not request.user.is_authenticated:
        return _json_forbidden()

    raw_ids = request.GET.get('strain_ids', '')
    if not raw_ids:
        return JsonResponse({'favorites': []})

    try:
        strain_ids = [int(value) for value in raw_ids.split(',') if value.strip()]
    except ValueError:
        return JsonResponse({'error': 'Invalid strain_ids'}, status=400)

    favorites = list(
        FavoriteStrain.objects.filter(
            user=request.user,
            strain_id__in=strain_ids,
        ).values_list('strain_id', flat=True)
    )
    return JsonResponse({'favorites': favorites})


@require_POST
def comment_submit(request):
    if not request.user.is_authenticated:
        return _json_forbidden()

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, TypeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    strain_id = data.get('strain_id')
    if not strain_id:
        return JsonResponse({'error': 'strain_id is required'}, status=400)

    strain = get_object_or_404(Strain, pk=strain_id, active=True)
    form = StrainCommentForm(data)
    if not form.is_valid():
        return JsonResponse({'errors': form.errors.get_json_data()}, status=400)

    moderation = moderate_strain_comment(
        form.cleaned_data['pros'],
        form.cleaned_data['cons'],
    )
    comment, _created = StrainComment.objects.update_or_create(
        user=request.user,
        strain=strain,
        defaults={
            'pros': form.cleaned_data['pros'],
            'cons': form.cleaned_data['cons'],
            'reaction': form.cleaned_data['reaction'],
            'status': moderation.status,
            'moderation_reason': moderation.reason,
        },
    )

    response_data = {
        'status': comment.status,
        'comment_id': comment.id,
    }

    if comment.status == 'approved':
        response_data['html'] = render_to_string(
            'partials/strain_comment_item.html',
            {'comment': comment},
            request=request,
        )

    return JsonResponse(response_data)


@require_GET
def comment_list(request):
    strain_id = request.GET.get('strain_id')
    if not strain_id:
        return JsonResponse({'error': 'strain_id is required'}, status=400)

    try:
        page_number = int(request.GET.get('page', 1))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Invalid page'}, status=400)

    if page_number < 1:
        return JsonResponse({'error': 'Invalid page'}, status=400)

    strain = get_object_or_404(Strain, pk=strain_id, active=True)
    paginator = Paginator(
        StrainComment.objects.select_related('user')
        .filter(strain=strain, status='approved')
        .order_by('-created_at'),
        STRAIN_COMMENTS_PAGE_SIZE,
    )

    try:
        page = paginator.page(page_number)
    except Exception as exc:
        if page_number == 1:
            raise Http404 from exc
        return JsonResponse({'html': '', 'has_more': False, 'next_page': None})

    html = render_to_string(
        'partials/strain_comments_items.html',
        {'comments': page.object_list},
        request=request,
    )
    return JsonResponse({
        'html': html,
        'has_more': page.has_next(),
        'next_page': page.next_page_number() if page.has_next() else None,
    })
