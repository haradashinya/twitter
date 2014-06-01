from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from twitter.models import UserProfile,Tweet

# Register your models here.

class UserProfileInline(admin.StackedInline):
    model = UserProfile


class UserAdmin(UserAdmin):
    inlines = [UserProfileInline]


class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'picture', 'desc')

class TweetAdmin(admin.ModelAdmin):
    list_display = ('text','created_date')



admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(Tweet,TweetAdmin)

