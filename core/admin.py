from django.contrib import admin
from .models import Empresa, Perfil, Cliente, Producto # etc.

admin.site.register(Empresa)
admin.site.register(Perfil)
admin.site.register(Cliente)
admin.site.register(Producto)