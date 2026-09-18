from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0026_academic_session_and_year_semester'),
    ]

    operations = [
        migrations.CreateModel(
            name='ChairmanDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200, verbose_name='শিরোনাম')),
                ('file', models.FileField(upload_to='chairman_documents/%Y/%m/',
                                          verbose_name='ফাইল')),
                ('note', models.TextField(blank=True,
                                          help_text='কন্ট্রোলারের জন্য ঐচ্ছিক বার্তা',
                                          verbose_name='নোট')),
                ('uploaded_at', models.DateTimeField(auto_now_add=True,
                                                     verbose_name='আপলোডের সময়')),
                ('is_sent', models.BooleanField(default=False,
                                                verbose_name='কন্ট্রোলারে পাঠানো হয়েছে')),
                ('sent_at', models.DateTimeField(blank=True, null=True,
                                                 verbose_name='পাঠানোর সময়')),
                ('uploaded_by', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='chairman_documents',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='আপলোডকারী')),
            ],
            options={
                'verbose_name': 'চেয়ারম্যানের ফাইল',
                'verbose_name_plural': 'চেয়ারম্যানের ফাইল',
                'ordering': ['-uploaded_at'],
            },
        ),
    ]
