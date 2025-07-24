from django.forms import ModelForm
from django import forms
from panel.models import Profile_Model
from django.contrib.auth.models import User


# Define las opciones de grupo
GROUP_CHOICES = [
    ('viewer', 'Solo Lectura'),
    ('crawler', 'Usuario Estándar'),
    ('admin', 'Administrador'),
    # ('', 'Ninguno'), # Opción para no asignar a ningún grupo
]

class UserCreateForm(forms.Form):
    username = forms.CharField(max_length=150, required=True, label="Nombre de Usuario")
    email = forms.EmailField(required=True, label="Correo Electrónico")
    password = forms.CharField(widget=forms.PasswordInput, required=True, label="Contraseña")
    password_confirm = forms.CharField(widget=forms.PasswordInput, required=True, label="Confirmar Contraseña")
    group_name = forms.ChoiceField(choices=GROUP_CHOICES, required=False, label="Grupo")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Agrega clase Bootstrap a todos los campos
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Este nombre de usuario ya está en uso.")
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Este correo electrónico ya está registrado.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', "Las contraseñas no coinciden.")
        return cleaned_data

class UserUpdateForm(forms.ModelForm):
    group_name = forms.ChoiceField(choices=GROUP_CHOICES, required=False, label="Grupo")

    class Meta:
        model = User
        #fields = ['username', 'email', 'is_active', 'is_staff', 'is_superuser'] # Puedes añadir o quitar campos
        fields = ['username', 'email'] # Puedes añadir o quitar campos

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Inicializa el campo group_name con el grupo actual del usuario
        if self.instance.pk:
            current_group = self.instance.groups.first()
            if current_group:
                self.fields['group_name'].initial = current_group.name

        # Agrega clase Bootstrap a todos los campos
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Este nombre de usuario ya está en uso.")
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Este correo electrónico ya está registrado.")
        return email


#=======================================================================================================================================
# OLD
#=======================================================================================================================================

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
