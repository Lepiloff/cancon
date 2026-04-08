from django import forms
from django.utils.translation import gettext_lazy as _
from apps.strains.models import (
    CATEGORY_CHOICES,
    COMMENT_REACTION_CHOICES,
    Feeling,
    Flavor,
    HelpsWith,
)


class StrainFilterForm(forms.Form):
    category = forms.MultipleChoiceField(choices=CATEGORY_CHOICES, required=False, widget=forms.CheckboxSelectMultiple)
    thc = forms.MultipleChoiceField(
        choices=[
            ('sin thc', _('Sin THC')),
            ('bajo thc', _('Bajo')),
            ('medio thc', _('Medio')),
            ('alto thc', _('Alto'))
        ],
        required=False,
        widget=forms.CheckboxSelectMultiple
    )
    feelings = forms.ModelMultipleChoiceField(
        queryset=Feeling.objects.all(), required=False, widget=forms.CheckboxSelectMultiple)
    helps_with = forms.ModelMultipleChoiceField(
        queryset=HelpsWith.objects.all(), required=False, widget=forms.CheckboxSelectMultiple)
    flavors = forms.ModelMultipleChoiceField(
        queryset=Flavor.objects.all(), required=False, widget=forms.CheckboxSelectMultiple)


class StrainCommentForm(forms.Form):
    pros = forms.CharField(
        required=False,
        max_length=600,
        widget=forms.Textarea(attrs={'rows': 3}),
    )
    cons = forms.CharField(
        required=False,
        max_length=600,
        widget=forms.Textarea(attrs={'rows': 3}),
    )
    reaction = forms.ChoiceField(choices=COMMENT_REACTION_CHOICES, required=True)

    def clean(self):
        cleaned_data = super().clean()
        pros = (cleaned_data.get('pros') or '').strip()
        cons = (cleaned_data.get('cons') or '').strip()

        if not pros and not cons:
            raise forms.ValidationError(_('Añade pros, contras o ambos.'))

        cleaned_data['pros'] = pros
        cleaned_data['cons'] = cons
        return cleaned_data
