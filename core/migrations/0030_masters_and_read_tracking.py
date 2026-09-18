from django.db import migrations, models


def backfill_masters_year(apps, schema_editor):
    """Give masters bills a usable heading.

    Bills whose old flat semester was literally 'মাস্টার্স' were skipped by
    migration 0026 because there was no year to map them onto. Now that
    'মাস্টার্স' is itself an academic_year choice, they can be filled in and
    will print as 'মাস্টার্স ১ম সেমিস্টার পরীক্ষা - <year>' once a session is set.
    """
    Bill = apps.get_model('core', 'Bill')
    Bill.objects.filter(semester='মাস্টার্স', academic_year__isnull=True).update(
        academic_year='মাস্টার্স', exam_semester='১ম সেমিস্টার')


def clear_masters_year(apps, schema_editor):
    Bill = apps.get_model('core', 'Bill')
    Bill.objects.filter(academic_year='মাস্টার্স').update(
        academic_year=None, exam_semester=None)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0029_chairman_year'),
    ]

    operations = [
        # Controller read-tracking on chairman uploads
        migrations.AddField(
            model_name='chairmandocument',
            name='is_read',
            field=models.BooleanField(default=False, verbose_name='কন্ট্রোলার দেখেছেন'),
        ),
        migrations.AddField(
            model_name='chairmandocument',
            name='read_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='দেখার সময়'),
        ),

        # Masters as an academic year
        migrations.AlterField(
            model_name='bill',
            name='academic_year',
            field=models.CharField(
                blank=True, null=True, max_length=20,
                choices=[('১ম বর্ষ', '১ম বর্ষ'), ('২য় বর্ষ', '২য় বর্ষ'),
                         ('৩য় বর্ষ', '৩য় বর্ষ'), ('৪র্থ বর্ষ', '৪র্থ বর্ষ'),
                         ('মাস্টার্স', 'মাস্টার্স')],
                verbose_name='বর্ষ'),
        ),
        migrations.AlterField(
            model_name='profile',
            name='chairman_year',
            field=models.CharField(
                blank=True, null=True, max_length=20,
                choices=[('১ম বর্ষ', '১ম বর্ষ'), ('২য় বর্ষ', '২য় বর্ষ'),
                         ('৩য় বর্ষ', '৩য় বর্ষ'), ('৪র্থ বর্ষ', '৪র্থ বর্ষ'),
                         ('মাস্টার্স', 'মাস্টার্স')],
                help_text='পদবী চেয়ারম্যান হলে কোন বর্ষের দায়িত্বে।',
                verbose_name='চেয়ারম্যানের বর্ষ'),
        ),
        migrations.RunPython(backfill_masters_year, clear_masters_year),
    ]
