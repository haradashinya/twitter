from django.contrib import admin
from django.conf import settings
import django

from django.conf.urls import url, include, patterns

urlpatterns = [
    url(r'', include('twitter.urls')),
    url(r'^admin/',include(admin.site.urls)),
    url(r'media/(?P<path>.*)', django.views.static.serve,
     {'document_root': settings.MEDIA_ROOT})
]
# django.views.static.serve

