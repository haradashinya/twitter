from django import forms
import datetime
from django.contrib.auth.models import User
from twitter.models import UserProfile, Tweet,Relationship


class UserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput())
    class Meta:
        model = User
        fields = ('username', 'password')



class TweetForm(forms.ModelForm):
    class Meta:
        model = Tweet
        fields = ('text',)

class UserProfileForm(forms.ModelForm):

    class Meta:
        model = UserProfile
        fields = ('picture',)






