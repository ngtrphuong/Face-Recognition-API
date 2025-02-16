"""myapp URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
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
from django.contrib import admin
from django.urls import path
from django.urls.conf import include
from django.conf.urls import url
from django.conf.urls.static import static
from django.views.generic import RedirectView
from . import settings
from attendance import views
from rest_framework_jwt.views import obtain_jwt_token
from rest_framework_jwt.views import refresh_jwt_token
from rest_framework_jwt.views import verify_jwt_token

urlpatterns = [
    path('admin/', admin.site.urls),
    path('attendance/', include("attendance.urls")),
    
    #authentication methods
    url('^api-auth/', include('rest_framework.urls'), name='api-login'),
    url('^api/token/', obtain_jwt_token),
    path('api/api-token-refresh/', refresh_jwt_token),
    path('api/api-token-verify/', verify_jwt_token),
    
    path(r'', include('django.contrib.auth.urls')),

    url('^$', RedirectView.as_view(url='attendance/')),
] + static((settings.MEDIA_URL),document_root=settings.MEDIA_ROOT)
