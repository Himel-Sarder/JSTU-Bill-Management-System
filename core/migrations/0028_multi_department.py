from django.db import migrations, models
import django.db.models.deletion


# Everything currently in the system belongs to this one department. Its name
# was spelled two different ways: the Bill model default used 'এবং' while the
# PDF templates printed 'ও'. Both collapse onto the single Department below.
DEFAULT_DEPARTMENT = 'কম্পিউটার বিজ্ঞান ও প্রকৌশল'
DEFAULT_SHORT = 'CSE'

# Old Bill.department strings that mean the same department
KNOWN_ALIASES = {
    'কম্পিউটার বিজ্ঞান এবং প্রকৌশল',
    'কম্পিউটার বিজ্ঞান ও প্রকৌশল',
    'কম্পিউটার বিজ্ঞান ও প্রকৌশল বিভাগ',
    'কম্পিউটার বিজ্ঞান এবং প্রকৌশল বিভাগ',
}


def create_departments_and_link(apps, schema_editor):
    """Turn the free-text Bill.department into real Department rows.

    Every distinct string already stored becomes a Department (aliases of the
    CSE spelling are merged), then every bill, profile and work type is
    pointed at the right one. Nothing is dropped: a value that doesn't match a
    known alias still gets its own Department rather than being discarded.
    """
    Department = apps.get_model('core', 'Department')
    Bill = apps.get_model('core', 'Bill')
    Profile = apps.get_model('core', 'Profile')

    default_dept, _ = Department.objects.get_or_create(
        name=DEFAULT_DEPARTMENT,
        defaults={'short_name': DEFAULT_SHORT, 'is_active': True, 'order': 0},
    )

    # Any other spelling that was actually used gets its own department
    existing = (Bill.objects.exclude(department__isnull=True)
                            .exclude(department='')
                            .values_list('department', flat=True).distinct())

    name_to_dept = {alias: default_dept for alias in KNOWN_ALIASES}
    for raw in existing:
        value = (raw or '').strip()
        if not value or value in name_to_dept:
            continue
        dept, _ = Department.objects.get_or_create(
            name=value, defaults={'is_active': True, 'order': 10})
        name_to_dept[value] = dept

    # Point every bill at its department
    for value, dept in name_to_dept.items():
        Bill.objects.filter(department=value).update(department_ref=dept.id)

    # Bills with a blank/unknown department fall back to the default
    Bill.objects.filter(department_ref__isnull=True).update(department_ref=default_dept.id)

    # Every existing user belongs to the department the system used to assume
    Profile.objects.filter(department__isnull=True).update(department=default_dept.id)

    # Existing work types stay shared across departments (department left NULL),
    # which keeps every current bill form working exactly as before.


def unlink_departments(apps, schema_editor):
    """Reverse: write the department name back into the text column."""
    Bill = apps.get_model('core', 'Bill')
    Department = apps.get_model('core', 'Department')
    for dept in Department.objects.all():
        Bill.objects.filter(department_ref=dept.id).update(department=dept.name)
    Profile = apps.get_model('core', 'Profile')
    Profile.objects.update(department=None)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0027_chairman_document'),
    ]

    operations = [
        # 1. The Department table
        migrations.CreateModel(
            name='Department',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150, unique=True,
                                          verbose_name='বিভাগের নাম')),
                ('short_name', models.CharField(blank=True, max_length=20,
                                                help_text='যেমন: CSE, EEE',
                                                verbose_name='সংক্ষিপ্ত নাম')),
                ('is_active', models.BooleanField(
                    default=True,
                    help_text='নিষ্ক্রিয় করলে নতুন বিল বা ব্যবহারকারীতে দেখা যাবে না।',
                    verbose_name='সক্রিয়')),
                ('order', models.PositiveIntegerField(default=0, verbose_name='ক্রম')),
            ],
            options={
                'verbose_name': 'বিভাগ',
                'verbose_name_plural': 'বিভাগসমূহ',
                'ordering': ['order', 'name'],
            },
        ),

        # 2. Department on users and work types
        migrations.AddField(
            model_name='profile',
            name='department',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='members', to='core.department',
                verbose_name='বিভাগ'),
        ),
        migrations.AddField(
            model_name='worktype',
            name='department',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.CASCADE,
                help_text='খালি রাখলে সব বিভাগের জন্য প্রযোজ্য হবে।',
                related_name='work_types', to='core.department',
                verbose_name='বিভাগ'),
        ),

        # 3. Temporary FK on Bill, populated from the old text column
        migrations.AddField(
            model_name='bill',
            name='department_ref',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='bills', to='core.department',
                verbose_name='বিভাগ'),
        ),
        migrations.RunPython(create_departments_and_link, unlink_departments),

        # 4. Swap the text column out for the FK
        migrations.RemoveField(model_name='bill', name='department'),
        migrations.RenameField(model_name='bill',
                               old_name='department_ref', new_name='department'),

        # 5. A work type name may repeat across departments
        migrations.AlterUniqueTogether(
            name='worktype',
            unique_together={('name', 'degree_type', 'department')},
        ),
    ]
