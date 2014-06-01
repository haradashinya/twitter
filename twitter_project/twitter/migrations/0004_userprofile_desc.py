# encoding: utf8
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('twitter', '0003_auto_20140501_0546'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='desc',
            field=models.TextField(default='', blank=True),
            preserve_default=False,
        ),
    ]
