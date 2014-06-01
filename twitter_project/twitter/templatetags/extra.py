from django import template
from twitter.models import User,Relationship,UserProfile
from django.template.defaultfilters import stringfilter

register = template.Library()



@register.filter
def cut(name):
    return name * 10



@register.filter(name='is_following')
def is_following(who_name,whom_name):
    """
    Build follow or unfllow button.
    """
    who = User.objects.get(username = who_name)
    whom = User.objects.get(username = whom_name)

    following_users = Relationship.objects.filter(who_id = who.id).all()
    if len(following_users) == 0:
        return False
    following_ids = [item.whom_id for item in following_users]

    if whom.id in following_ids:
        return True
    return False









