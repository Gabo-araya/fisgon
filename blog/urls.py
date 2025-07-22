from django.urls import path
import blog.views

urlpatterns = [

#article
    path('articulos/', blog.views.listar_articulos, name='listar_articulos'),
    path('articulos/<int:id>/', blog.views.ver_articulo, name='ver_articulo'),
    path('articulos/crear/', blog.views.crear_articulo, name='crear_articulo'),
    path('articulos/modificar/<int:id>/', blog.views.modificar_articulo, name='modificar_articulo'),
    path('articulos/eliminar/<int:id>/', blog.views.eliminar_articulo, name='eliminar_articulo'),

#category
    path('categorias/', blog.views.listar_categorias, name='listar_categorias'),
    path('categorias/<int:id>/', blog.views.ver_categoria, name='ver_categoria'),
    path('categorias/crear/', blog.views.crear_categoria, name='crear_categoria'),
    path('categorias/modificar/<int:id>/', blog.views.modificar_categoria, name='modificar_categoria'),
    path('categorias/eliminar/<int:id>/', blog.views.eliminar_categoria, name='eliminar_categoria'),

#image_article
    path('imagen_articulo/', blog.views.listar_imagen_articulos, name='listar_imagen_articulos'),
    path('imagen_articulo/<int:id>/', blog.views.ver_imagen_articulo, name='ver_imagen_articulo'),
    path('imagen_articulo/crear/', blog.views.crear_imagen_articulo, name='crear_imagen_articulo'),
    path('imagen_articulo/modificar/<int:id>/', blog.views.modificar_imagen_articulo, name='modificar_imagen_articulo'),
    path('imagen_articulo/eliminar/<int:id>/', blog.views.eliminar_imagen_articulo, name='eliminar_imagen_articulo'),

]
