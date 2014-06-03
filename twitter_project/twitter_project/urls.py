from django.contrib import admin
from django.conf import settings
import django

from django.conf.urls import url, include, patterns

print("static url is")
print(settings.STATIC_ROOT)
urlpatterns = [
    url(r'', include('twitter.urls')),
    url(r'^admin/',include(admin.site.urls)),
    url(r'media/(?P<path>.*)', django.views.static.serve,
     {'document_root': settings.MEDIA_ROOT}),
    url(r'^static/(?P<path>.*)$', 'django.views.static.serve', {'document_root' : settings.STATIC_ROOT})
]


# django.views.static.serve

