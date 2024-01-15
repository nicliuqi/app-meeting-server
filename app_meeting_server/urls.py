"""community_meetings URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
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
from django.urls import path, include
from django.conf import settings

if settings.FOR_OPENEULER:
    urlpatterns = [
        path('', include('openeuler.urls')),
    ]
elif settings.FOR_MINDSPORE:
    urlpatterns = [
        path('', include('mindspore.urls')),
    ]
elif settings.FOR_OPENGAUSS:
    urlpatterns = [
        path('', include('opengauss.urls')),
    ]
else:
    urlpatterns = list()
