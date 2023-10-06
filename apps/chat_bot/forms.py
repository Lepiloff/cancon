from django import forms


class ChatForm(forms.Form):
    message = forms.CharField(widget=forms.Textarea(attrs={'rows': 4, 'cols': 50}), label='')
