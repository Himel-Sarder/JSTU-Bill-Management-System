from django.db import migrations, models


# The old scheme encoded the chairman's year in the username
USERNAME_TO_YEAR = {
    'JSTUChairman1': ('১ম বর্ষ', 'signature_chairman1'),
    'JSTUChairman2': ('২য় বর্ষ', 'signature_chairman2'),
    'JSTUChairman3': ('৩য় বর্ষ', 'signature_chairman3'),
    'JSTUChairman4': ('৪র্থ বর্ষ', 'signature_chairman4'),
}


def assign_chairman_years(apps, schema_editor):
    """Turn the JSTUChairman1..4 naming convention into real data.

    Each of those accounts gets chairman_year set, and its numbered signature
    copied onto the single signature_chairman field. The numbered fields are
    left in place, so nothing is lost and the fallback in
    Profile.active_chairman_signature still works either way.
    """
    Profile = apps.get_model('core', 'Profile')

    for username, (year, legacy_field) in USERNAME_TO_YEAR.items():
        for profile in Profile.objects.filter(user__username=username):
            profile.chairman_year = year
            legacy_value = getattr(profile, legacy_field, None)
            if legacy_value and not profile.signature_chairman:
                profile.signature_chairman = legacy_value
            profile.save(update_fields=['chairman_year', 'signature_chairman'])

    # Any other chairman account has no year yet; the admin assigns it. Those
    # accounts simply see no year-specific bills until then, which is the same
    # safe default used elsewhere (fail closed, not open).


def clear_chairman_years(apps, schema_editor):
    Profile = apps.get_model('core', 'Profile')
    Profile.objects.update(chairman_year=None, signature_chairman=None)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0028_multi_department'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='chairman_year',
            field=models.CharField(
                blank=True, null=True, max_length=20,
                choices=[('১ম বর্ষ', '১ম বর্ষ'), ('২য় বর্ষ', '২য় বর্ষ'),
                         ('৩য় বর্ষ', '৩য় বর্ষ'), ('৪র্থ বর্ষ', '৪র্থ বর্ষ')],
                help_text='পদবী চেয়ারম্যান হলে কোন বর্ষের দায়িত্বে।',
                verbose_name='চেয়ারম্যানের বর্ষ'),
        ),
        migrations.AddField(
            model_name='profile',
            name='signature_chairman',
            field=models.ImageField(
                blank=True, null=True,
                upload_to='signatures/chairman/',
                verbose_name='চেয়ারম্যানের স্বাক্ষর'),
        ),
        migrations.RunPython(assign_chairman_years, clear_chairman_years),
    ]
