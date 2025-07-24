from panel.models import Profile_Model
# from django.contrib.auth.models import Group

#=======================================================================================================================================
# Vista de inicio
#=======================================================================================================================================

def info_header_user(request, *args, **kwargs):
    # if request.user.groups.filter(name='admin').exists():
    #     # return Profile_Model.objects.get(user=request.user.id)
    #     return request.user.id

    # group = None
    # if request.user.groups.exists():
    #     group = request.user.groups.all()[0].name
    # else:
    #     group = 'viewer'

    # user_actual = request.user.id
    # print(f'user_actual: {request.user}')
    #
    # pass
    # return group
    return request.user



def user_group(request, *args, **kwargs):
    '''Opciones: admin, crawler, viewer (default).'''

    user_group = None
    if request.user.groups.exists():
        # user_group = request.user.groups.all()[0].name
        user_group = request.user.groups.first().name
    else:
        user_group = 'viewer'

    return user_group


def is_admin(user):
    '''Verifica si el usuario pertenece al grupo 'admin'.'''
    return user.groups.filter(name='admin').exists()
