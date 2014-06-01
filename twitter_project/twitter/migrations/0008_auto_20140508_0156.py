# encoding: utf8
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('twitter', '0007_tweet_text'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='tweet',
            name='created_date',
        ),
        migrations.RemoveField(
            model_name='tweet',
            name='text',
        ),
        migrations.AlterField(
            model_name='tweet',
            name='user',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL, to_field='id'),
        ),
    ]
