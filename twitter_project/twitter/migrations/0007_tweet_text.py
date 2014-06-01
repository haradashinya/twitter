# encoding: utf8
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('twitter', '0006_remove_tweet_text'),
    ]

    operations = [
        migrations.AddField(
            model_name='tweet',
            name='text',
            field=models.TextField(default=''),
            preserve_default=False,
        ),
    ]
