from django.db import models
# from django.contrib.auth.models import User


#=======================================================================================================================================
# Article
#=======================================================================================================================================

class Article_Model(models.Model):
    name = models.CharField(max_length=150, default='Sin nombre', verbose_name='Nombre [*]')
    title = models.CharField(max_length=150, default='Sin título', verbose_name='Título [*]')
    subtitle = models.CharField(max_length=250, null=True, blank=True, verbose_name='Subtítulo')
    abstract = models.TextField(null=True, blank=True, verbose_name='Resumen')
    content = models.TextField(verbose_name='Contenido [*]')
    date = models.DateField(verbose_name='Fecha')
    fk_categoria = models.ForeignKey('Category_Model', on_delete=models.DO_NOTHING, verbose_name='Categoría [*]')
    #fk_agent = models.ForeignKey('agent.Agent_Model', on_delete=models.DO_NOTHING, null=True, blank=True, verbose_name='Agente')

    image_main = models.ImageField(null=True, blank=True, upload_to='img_article/', default='', verbose_name='Imagen principal')

    draft = models.BooleanField(null=True, blank=True, verbose_name='Borrador')
    #fk_autor = models.ForeignKey(User, on_delete=models.DO_NOTHING, null=True, blank=True, verbose_name='Autor')

    class Meta:
        ''' Define el nombre singular y plural, y el ordenamiento de los elementos.'''
        verbose_name = 'Artículo'
        verbose_name_plural = 'Artículos'
        ordering = ['-date']

    def __str__(self):
        return self.name


#=======================================================================================================================================
# Category
#=======================================================================================================================================

class Category_Model(models.Model):
    name = models.CharField(max_length=250, verbose_name='Nombre')
    description = models.TextField(null=True, blank=True, default='', verbose_name='Descripción')

    class Meta:
        ''' Define el nombre singular y plural, y el ordenamiento de los elementos.'''
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
        ordering = ['-id']

    def __str__(self):
        return self.name


#=======================================================================================================================================
# Image
#=======================================================================================================================================

class Image_Article_Model(models.Model):
    name = models.CharField(max_length=150, verbose_name='Nombre [*]')
    image = models.ImageField(upload_to='img_article/', default='', verbose_name='Imagen [*]')
    date = models.DateTimeField(verbose_name='Fecha de publicación [*]')

    class Meta:
        ''' Define el nombre singular y plural, y el ordenamiento de los elementos.'''
        verbose_name = 'Imagen de artículo'
        verbose_name_plural = 'Imágenes de artículos'
        ordering = ['-date']

    def __str__(self):
        return self.name
