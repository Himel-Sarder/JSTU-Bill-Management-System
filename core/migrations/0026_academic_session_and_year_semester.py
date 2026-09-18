from django.db import migrations, models
import django.db.models.deletion


# Old flat semester value -> (year, semester)
LEGACY_MAP = {
    '১ম সেমিস্টার': ('১ম বর্ষ', '১ম সেমিস্টার'),
    '২য় সেমিস্টার': ('১ম বর্ষ', '২য় সেমিস্টার'),
    '৩য় সেমিস্টার': ('২য় বর্ষ', '১ম সেমিস্টার'),
    '৪র্থ সেমিস্টার': ('২য় বর্ষ', '২য় সেমিস্টার'),
    '৫ম সেমিস্টার': ('৩য় বর্ষ', '১ম সেমিস্টার'),
    '৬ষ্ঠ সেমিস্টার': ('৩য় বর্ষ', '২য় সেমিস্টার'),
    '৭ম সেমিস্টার': ('৪র্থ বর্ষ', '১ম সেমিস্টার'),
    '৮ম সেমিস্টার': ('৪র্থ বর্ষ', '২য় সেমিস্টার'),
}


def backfill_year_and_semester(apps, schema_editor):
    """Split every existing bill's flat semester into year + semester.

    '৫ম সেমিস্টার' becomes '৩য় বর্ষ' + '১ম সেমিস্টার'. Masters bills (whose
    semester was literally 'মাস্টার্স') have no year/semester equivalent, so
    they keep only their legacy value and still render via the fallback in
    Bill.exam_title.
    """
    Bill = apps.get_model('core', 'Bill')
    for legacy, (year, semester) in LEGACY_MAP.items():
        Bill.objects.filter(semester=legacy).update(
            academic_year=year, exam_semester=semester
        )


def clear_year_and_semester(apps, schema_editor):
    """Reverse step: the legacy `semester` column is untouched, so just blank
    the derived columns."""
    Bill = apps.get_model('core', 'Bill')
    Bill.objects.all().update(academic_year=None, exam_semester=None)


def seed_sessions(apps, schema_editor):
    """Give the admin a few sensible sessions to start from.

    Only runs when the table is empty, so it never fights with sessions the
    admin has already entered.
    """
    AcademicSession = apps.get_model('core', 'AcademicSession')
    if AcademicSession.objects.exists():
        return
    for start in range(2019, 2027):
        AcademicSession.objects.create(
            start_year=start, end_year=start + 1, is_active=True
        )


def drop_seeded_sessions(apps, schema_editor):
    AcademicSession = apps.get_model('core', 'AcademicSession')
    AcademicSession.objects.filter(bills__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0025_fix_profile_picture_default'),
    ]

    operations = [
        migrations.CreateModel(
            name='AcademicSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name='ID')),
                ('start_year', models.PositiveIntegerField(verbose_name='সেশন শুরুর বছর')),
                ('end_year', models.PositiveIntegerField(verbose_name='সেশন শেষের বছর')),
                ('is_active', models.BooleanField(
                    default=True,
                    help_text='নিষ্ক্রিয় করলে নতুন বিলে এই সেশনটি আর দেখা যাবে না।',
                    verbose_name='সক্রিয়')),
            ],
            options={
                'verbose_name': 'শিক্ষাবর্ষ (সেশন)',
                'verbose_name_plural': 'শিক্ষাবর্ষ (সেশন)',
                'ordering': ['-start_year'],
                'unique_together': {('start_year', 'end_year')},
            },
        ),
        migrations.AddField(
            model_name='bill',
            name='academic_year',
            field=models.CharField(
                blank=True, null=True, max_length=20,
                choices=[('১ম বর্ষ', '১ম বর্ষ'), ('২য় বর্ষ', '২য় বর্ষ'),
                         ('৩য় বর্ষ', '৩য় বর্ষ'), ('৪র্থ বর্ষ', '৪র্থ বর্ষ')],
                verbose_name='বর্ষ'),
        ),
        migrations.AddField(
            model_name='bill',
            name='exam_semester',
            field=models.CharField(
                blank=True, null=True, max_length=20,
                choices=[('১ম সেমিস্টার', '১ম সেমিস্টার'), ('২য় সেমিস্টার', '২য় সেমিস্টার')],
                verbose_name='সেমিস্টার'),
        ),
        migrations.AddField(
            model_name='bill',
            name='session',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='bills', to='core.academicsession',
                verbose_name='সেশন'),
        ),
        migrations.AlterField(
            model_name='bill',
            name='semester',
            field=models.CharField(
                blank=True, null=True, max_length=20,
                choices=[('১ম সেমিস্টার', '১ম সেমিস্টার'), ('২য় সেমিস্টার', '২য় সেমিস্টার'),
                         ('৩য় সেমিস্টার', '৩য় সেমিস্টার'), ('৪র্থ সেমিস্টার', '৪র্থ সেমিস্টার'),
                         ('৫ম সেমিস্টার', '৫ম সেমিস্টার'), ('৬ষ্ঠ সেমিস্টার', '৬ষ্ঠ সেমিস্টার'),
                         ('৭ম সেমিস্টার', '৭ম সেমিস্টার'), ('৮ম সেমিস্টার', '৮ম সেমিস্টার'),
                         ('মাস্টার্স', 'মাস্টার্স')],
                verbose_name='সেমিস্টার (পুরাতন)'),
        ),
        migrations.RunPython(backfill_year_and_semester, clear_year_and_semester),
        migrations.RunPython(seed_sessions, drop_seeded_sessions),
    ]
