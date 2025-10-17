from django import forms
from django.utils.translation import gettext_lazy as _
from apps.strains.models import CATEGORY_CHOICES, Feeling, HelpsWith, Flavor


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

