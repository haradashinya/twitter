# encoding: utf8
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('twitter', '0004_userprofile_desc'),
    ]

    operations = [
        migrations.CreateModel(
            name='Tweet',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('text', models.CharField(max_length=140)),
                ('created_date', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(to='twitter.UserProfile', to_field='id')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
