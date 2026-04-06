import json

from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from apps.strains.models import FavoriteStrain, Strain


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
