"""
URL configuration for drone project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import os

from django.contrib import admin
from django.conf import settings
from django.urls import include, path
from django.conf.urls.static import static
from django.views.generic import RedirectView

from core import api_views

FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://127.0.0.1:5173/')

urlpatterns = [
    path('', RedirectView.as_view(url=FRONTEND_URL, permanent=False)),
    path('admin/', admin.site.urls),
    path('api/', include('core.urls', namespace='core-api')),
    path('media/<path:path>', api_views.media_file, name='media-file'),
]

# Railway 使用持久化卷保存上传图片；通过 Django 提供媒体文件，供前端反向代理访问。
if settings.DEBUG or os.environ.get('DJANGO_SERVE_MEDIA', '1') == '1':
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

