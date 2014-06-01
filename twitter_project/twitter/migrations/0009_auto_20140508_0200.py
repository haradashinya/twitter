# encoding: utf8
from __future__ import unicode_literals

from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('twitter', '0008_auto_20140508_0156'),
    ]

    operations = [
        migrations.AddField(
            model_name='tweet',
            name='text',
            field=models.TextField(default=''),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='tweet',
            name='created_date',
            field=models.DateTimeField(default=datetime.datetime(2014, 5, 8, 2, 0, 47, 245465), auto_now=True),
            preserve_default=False,
        ),
    ]
