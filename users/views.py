import json

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from apps.strains.models import FavoriteStrain, Strain, StrainComment

from .forms import ConsumptionNoteForm
from .models import ConsumptionNote


def _wants_json(request):
    accept = request.headers.get('accept', '')
    return (
        request.headers.get('x-requested-with') == 'XMLHttpRequest'
        or 'application/json' in accept
    )


def _load_payload(request):
    if request.content_type and 'application/json' in request.content_type:
        try:
            return json.loads(request.body or '{}')
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
    return request.POST


def _serialize_note(note):
    return {
        'id': note.id,
        'date': note.date.isoformat(),
        'strain_id': note.strain_id,
        'strain_name_text': note.strain_name_text,
        'strain_label': note.strain_label,
        'notes': note.notes,
        'mood_before': note.mood_before,
        'mood_after': note.mood_after,
        'method': note.method,
        'created_at': note.created_at.isoformat() if note.created_at else None,
        'updated_at': note.updated_at.isoformat() if note.updated_at else None,
    }


def _save_consumption_note(user, form, note=None):
    strain = None
    strain_id = form.cleaned_data.get('strain_id')
    if strain_id:
        strain = get_object_or_404(Strain, pk=strain_id, active=True)

    if note is None:
        note = ConsumptionNote(user=user)

    note.user = user
    note.strain = strain
    note.strain_name_text = form.cleaned_data['strain_name_text'] or (strain.name if strain else '')
    note.date = form.cleaned_data['date']
    note.notes = form.cleaned_data.get('notes', '')
    note.mood_before = form.cleaned_data.get('mood_before')
    note.mood_after = form.cleaned_data.get('mood_after')
    note.method = form.cleaned_data.get('method', '')
    note.save()
    return note


def _journal_queryset(user):
    return (
        ConsumptionNote.objects.select_related('strain')
        .filter(user=user)
        .order_by('-date', '-created_at')
    )


def _dashboard_counts(user):
    return {
        'favorite_count': FavoriteStrain.objects.filter(user=user).count(),
        'comment_count': StrainComment.objects.filter(user=user).count(),
        'note_count': ConsumptionNote.objects.filter(user=user).count(),
    }


def _dashboard_recent_context(user):
    return {
        'recent_favorites': list(
            FavoriteStrain.objects.select_related('strain')
            .filter(user=user)
            .order_by('-created_at')[:4]
        ),
        'recent_comments': list(
            StrainComment.objects.select_related('strain')
            .filter(user=user)
            .order_by('-created_at')[:4]
        ),
        'recent_notes': list(
            ConsumptionNote.objects.select_related('strain')
            .filter(user=user)
            .order_by('-date', '-created_at')[:4]
        ),
    }


def _journal_form_for_note(note=None):
    if note is None:
        return ConsumptionNoteForm(initial={'date': timezone.localdate()})

    return ConsumptionNoteForm(
        initial={
            'date': note.date,
            'strain_id': note.strain_id,
            'strain_name_text': note.strain_name_text or (note.strain.name if note.strain else ''),
            'notes': note.notes,
            'mood_before': note.mood_before,
            'mood_after': note.mood_after,
            'method': note.method,
        }
    )


def _journal_context(user, *, form=None, editing_note=None, status=200):
    notes_qs = _journal_queryset(user)
    page = Paginator(notes_qs, 12).get_page(None)
    context = {
        **_dashboard_counts(user),
        'dashboard_section': 'journal',
        'note_page': page,
        'note_items': page.object_list,
        'note_form': form or _journal_form_for_note(editing_note),
        'editing_note': editing_note,
        'strain_autocomplete_url': reverse('strains_api:strain_autocomplete'),
    }
    return context, status


@login_required
def dashboard(request):
    context = {
        **_dashboard_counts(request.user),
        **_dashboard_recent_context(request.user),
        'dashboard_section': 'overview',
    }
    return render(request, 'dashboard/dashboard.html', context)


@login_required
def dashboard_favorites(request):
    favorites_qs = (
        FavoriteStrain.objects.select_related('strain')
        .filter(user=request.user)
        .order_by('-created_at')
    )
    page = Paginator(favorites_qs, 12).get_page(request.GET.get('page'))
    context = {
        **_dashboard_counts(request.user),
        'dashboard_section': 'favorites',
        'favorite_page': page,
        'favorite_items': page.object_list,
    }
    return render(request, 'dashboard/favorites.html', context)


@login_required
def dashboard_comments(request):
    comments_qs = (
        StrainComment.objects.select_related('strain')
        .filter(user=request.user)
        .order_by('-created_at')
    )
    page = Paginator(comments_qs, 12).get_page(request.GET.get('page'))
    context = {
        **_dashboard_counts(request.user),
        'dashboard_section': 'comments',
        'comment_page': page,
        'comment_items': page.object_list,
    }
    return render(request, 'dashboard/comments.html', context)


@login_required
def dashboard_journal(request):
    page = Paginator(_journal_queryset(request.user), 12).get_page(request.GET.get('page'))
    edit_note = None
    edit_note_id = request.GET.get('edit')
    if edit_note_id:
        try:
            edit_note = ConsumptionNote.objects.select_related('strain').get(
                pk=int(edit_note_id),
                user=request.user,
            )
        except (TypeError, ValueError, ConsumptionNote.DoesNotExist):
            edit_note = None

    context = {
        **_dashboard_counts(request.user),
        'dashboard_section': 'journal',
        'note_page': page,
        'note_items': page.object_list,
        'note_form': _journal_form_for_note(edit_note),
        'editing_note': edit_note,
        'strain_autocomplete_url': reverse('strains_api:strain_autocomplete'),
    }
    return render(request, 'dashboard/journal.html', context)


@login_required
def dashboard_settings(request):
    context = {
        **_dashboard_counts(request.user),
        'dashboard_section': 'settings',
        'account_user': request.user,
    }
    return render(request, 'dashboard/settings.html', context)


@login_required
@require_POST
def journal_create(request):
    payload = _load_payload(request)
    if payload is None:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    form = ConsumptionNoteForm(payload)
    if not form.is_valid():
        if _wants_json(request):
            return JsonResponse({'errors': form.errors.get_json_data()}, status=400)
        return render(
            request,
            'dashboard/journal.html',
            _journal_context(request.user, form=form, status=400)[0],
            status=400,
        )

    note = _save_consumption_note(request.user, form)
    if _wants_json(request):
        return JsonResponse({'status': 'created', 'note': _serialize_note(note)})
    return redirect(reverse('dashboard_journal'))


@login_required
@require_POST
def journal_update(request, note_id):
    note = get_object_or_404(ConsumptionNote, pk=note_id, user=request.user)
    payload = _load_payload(request)
    if payload is None:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    form = ConsumptionNoteForm(payload)
    if not form.is_valid():
        if _wants_json(request):
            return JsonResponse({'errors': form.errors.get_json_data()}, status=400)
        return render(
            request,
            'dashboard/journal.html',
            _journal_context(request.user, form=form, editing_note=note, status=400)[0],
            status=400,
        )

    note = _save_consumption_note(request.user, form, note=note)
    if _wants_json(request):
        return JsonResponse({'status': 'updated', 'note': _serialize_note(note)})
    return redirect(reverse('dashboard_journal'))


@login_required
@require_POST
def journal_delete(request, note_id):
    note = get_object_or_404(ConsumptionNote, pk=note_id, user=request.user)
    note.delete()
    if _wants_json(request):
        return JsonResponse({'status': 'deleted', 'note_id': note_id})
    return redirect(reverse('dashboard_journal'))


@login_required
@require_GET
def journal_note_json(request, note_id):
    note = get_object_or_404(ConsumptionNote, pk=note_id, user=request.user)
    return JsonResponse({'note': _serialize_note(note)})
