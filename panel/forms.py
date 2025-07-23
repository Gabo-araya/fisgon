from django.forms import ModelForm
from django import forms
from panel.models import Profile_Model
from django.contrib.auth.models import User

class ProfileForm(ModelForm):
    class Meta:
        model = Profile_Model
        exclude = ['user']
        widgets = {
            'image': forms.FileInput(),
            'displayname': forms.TextInput(attrs={'placeholder': 'Agregar nombre'}),
            'info': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Agregar información'}),
        }


class EmailForm(ModelForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['email']
