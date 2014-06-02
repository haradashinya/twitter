# encoding: utf8
from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('twitter', '0009_auto_20140508_0200'),
    ]

    operations = [
        migrations.CreateModel(
            name='Relationship',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', auto_created=True, primary_key=True)),
                ('who_id', models.IntegerField()),
                ('whom_id', models.IntegerField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
