from django.contrib import admin

# Importar modelos desde apps de backend
from panel.models import Profile_Model
from blog.models import Article_Model, Category_Model, Image_Article_Model

# Registrar modelos en admin
admin.site.register(Article_Model)
admin.site.register(Category_Model)
admin.site.register(Image_Article_Model)
admin.site.register(Profile_Model)
