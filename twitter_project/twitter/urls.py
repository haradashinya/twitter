from django.conf.urls import url, include, patterns
from twitter import views


urlpatterns = patterns('',
                       url(r'^$', views.index, name='index'),
                       url(r'^login$', views.user_login, name='login'),
                       url(r'^(?P<user_name>(\w)+)/edit$',views.user_edit,name='edit_user'),
                       url(r'^(?P<user_name>(\w)+)/tweets/new$', views.new_tweet, name='new_tweet'),
                       url(r'^logout$', views.user_logout, name='logout'),
                       url(r'^register$', views.user_register, name='register'),
                       url(r'^tweets/(?P<user_name>(\w)+)$', views.user_timeline, name='a'),
                       # url(r'^tweets/(?P<user_name>(\w)+)/followers$',views.followers_timeline,name='followers_timeline'),
                       url(r'^tweets/(?P<user_name>(\w)+)/followings$',views.followings_timeline,name='followers_timeline'),
                       url(r'^tweets/(?P<user_name>(\w)+)/relationship$',views.relationship,name='relationship'),
                       url(r'^about$',views.about)
                       )



