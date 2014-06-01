# encoding: utf8
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('twitter', '0005_tweet'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='tweet',
            name='text',
        ),
    ]
