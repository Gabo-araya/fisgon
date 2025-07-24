from django.contrib import admin

# Importar modelos desde apps de backend
from panel.models import Profile_Model

# Registrar modelos en admin
admin.site.register(Profile_Model)
