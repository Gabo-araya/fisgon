from django.db import models
from django.contrib.auth.models import User
from django.templatetags.static import static

class Profile_Model(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='avatars/', null=True, blank=True)
    displayname = models.CharField(max_length=20, null=True, blank=True)
    info = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = 'Perfil'
        verbose_name_plural = 'Perfiles'
        ordering = ['-id']

    def __str__(self):
        return str(self.user)

    # @property
    # def name(self):
    #     if self.displayname:
    #         name = self.displayname
    #     else:
    #         name = self.user.username
    #     return name

    # @property
    # def avatar(self):
    #     try:
    #         avatar = self.image.url
    #     except:
    #         avatar = static('panel/images/default_avatar_crawler.png')
    #     return avatar
