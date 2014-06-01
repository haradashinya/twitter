from django.contrib.auth.models import User
from django.template.defaultfilters import stringfilter
from django.db import models
from django.shortcuts import render, redirect
from django.contrib.sessions.backends.db import SessionStore

# Create your models here.

class UserProfile(models.Model):
    user = models.OneToOneField(User,related_name='profile')
    picture = models.ImageField(upload_to="pictures", blank=True)
    desc = models.TextField(blank=True)

    def followers(self):
        """
        return user's all followers
        """
        follower_ids = [follower.who_id for follower in Relationship.objects.filter(whom_id = self.user.id).all()]
        res = []
        for follower_id in follower_ids:
            res.append(User.objects.get(id = follower_id))
        return res


    @property
    def tweets(self):
        return Tweet.objects.filter(user_id = self.user.id).all()


    def followings(self):
        """
        return all following users
        """

        following_ids = [following.whom_id for following in Relationship.objects.filter(who_id = self.user.id).all()]
        res = []
        for following_id in following_ids:
            res.append(User.objects.get(id = following_id))
        return res


class Tweet(models.Model):
    user = models.ForeignKey(User, related_name='tweets')
    text = models.TextField(blank=False, default="")
    created_date = models.DateTimeField(auto_now=True)

    @property
    def pretty_text(self):
        """
        """
        len_char_line = 70
        lines= len(self.text) % len_char_line
        total = ""
        for i in range(0,lines):
            try:
                total += self.text[i*len_char_line:(i+1)*len_char_line]
                total += "\n"
            except:
                pass


        return  total

class Relationship(models.Model):
    who_id = models.IntegerField()
    whom_id  = models.IntegerField()

    def __str__(self):
        return str("<who_id: {}, whom_id: {}>".format(self.who_id,self.whom_id))


