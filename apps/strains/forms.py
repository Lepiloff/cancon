from django import forms
from apps.strains.models import CATEGORY_CHOICES, Feeling, HelpsWith, Flavor


class StrainFilterForm(forms.Form):
    category = forms.MultipleChoiceField(choices=CATEGORY_CHOICES, required=False, widget=forms.CheckboxSelectMultiple)
    thc = forms.MultipleChoiceField(
        choices=[('sin thc', 'Sin THC'), ('bajo thc', 'Bajo'), ('medio thc', 'Medio'), ('alto thc', 'Alto')],
        required=False,
        widget=forms.CheckboxSelectMultiple
    )
    feelings = forms.ModelMultipleChoiceField(
        queryset=Feeling.objects.all(), required=False, widget=forms.CheckboxSelectMultiple)
    helps_with = forms.ModelMultipleChoiceField(
        queryset=HelpsWith.objects.all(), required=False, widget=forms.CheckboxSelectMultiple)
    flavors = forms.ModelMultipleChoiceField(
        queryset=Flavor.objects.all(), required=False, widget=forms.CheckboxSelectMultiple)

