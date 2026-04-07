from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from django.contrib.auth.forms import UserCreationForm, UserChangeForm

from .models import ConsumptionNote
from .models import CustomUser


class CustomUserCreationForm(UserCreationForm):

    class Meta:
        model = CustomUser
        fields = ("email", "display_name")


class CustomUserChangeForm(UserChangeForm):

    class Meta:
        model = CustomUser
        fields = ("email", "display_name")


class ConsumptionNoteForm(forms.Form):
    date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    strain_id = forms.IntegerField(
        required=False,
        min_value=1,
        widget=forms.HiddenInput(),
    )
    strain_name_text = forms.CharField(required=False, max_length=255)
    notes = forms.CharField(
        required=False,
        max_length=5000,
        widget=forms.Textarea(attrs={'rows': 5}),
    )
    mood_before = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=5,
        widget=forms.NumberInput(attrs={'min': 1, 'max': 5}),
    )
    mood_after = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=5,
        widget=forms.NumberInput(attrs={'min': 1, 'max': 5}),
    )
    method = forms.ChoiceField(
        required=False,
        choices=ConsumptionNote.METHOD_CHOICES,
    )

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data['date'] = cleaned_data.get('date') or timezone.localdate()
        cleaned_data['strain_name_text'] = (cleaned_data.get('strain_name_text') or '').strip()

        if not cleaned_data.get('strain_id') and not cleaned_data['strain_name_text']:
            raise forms.ValidationError(
                _('Añade una variedad o un nombre manual para la entrada.')
            )

        return cleaned_data
