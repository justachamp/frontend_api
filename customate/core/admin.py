from django.contrib import admin

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin, GroupAdmin, Group as BaseGroupModel
from .models import User

# admin.site.unregister(BaseGroupModel)
# admin.site.register(Group, GroupAdmin)
admin.site.register(User, UserAdmin)
