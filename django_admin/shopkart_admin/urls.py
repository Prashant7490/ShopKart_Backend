from django.contrib import admin
from django.urls import path

# Admin panel ka title customize karo
admin.site.site_header  = "🛒 ShopKart Admin"
admin.site.site_title   = "ShopKart Admin"
admin.site.index_title  = "Manage Your Store"

urlpatterns = [
    path('admin/', admin.site.urls),
]
