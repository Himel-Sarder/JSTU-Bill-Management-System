from django.db import migrations, models


PHANTOM_DEFAULT = 'profile_pics/default.png'


def clear_phantom_default(apps, schema_editor):
    """Blank out rows still pointing at the non-existent default image.

    The old field had `default='profile_pics/default.png'`, but that file was
    never part of the project. Every profile created since then stores that
    path, which renders as a broken image. Those rows are set to empty so the
    template falls back to the generated initials avatar.
    """
    Profile = apps.get_model('core', 'Profile')
    Profile.objects.filter(profile_picture=PHANTOM_DEFAULT).update(profile_picture='')


def restore_phantom_default(apps, schema_editor):
    """Reverse step: put the old sentinel back on blank rows."""
    Profile = apps.get_model('core', 'Profile')
    Profile.objects.filter(profile_picture__in=['', None]).update(
        profile_picture=PHANTOM_DEFAULT
    )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0024_merge_20260718_1211'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='profile_picture',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='profile_pics/',
                verbose_name='প্রোফাইল ছবি',
            ),
        ),
        migrations.RunPython(clear_phantom_default, restore_phantom_default),
    ]
