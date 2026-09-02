from django.db import migrations, models
from django.conf import settings


def clean_orphan_owners(apps, schema_editor):
    """Delete rows whose ``owner`` is NULL before tightening the FK to NOT NULL.

    Under the owner-scoped multi-tenant isolation every queryset is filtered on
    ``owner=request.user``, so a row with ``owner=NULL`` is invisible to *every*
    user — it is dead data. We must remove these orphans before the schema can
    enforce NOT NULL (otherwise the ALTER TABLE would fail on existing rows).
    """
    Project = apps.get_model('schedule', 'Project')
    Assignment = apps.get_model('schedule', 'Assignment')
    # Child rows first to avoid FK cascade surprises.
    Assignment.objects.filter(owner__isnull=True).delete()
    Project.objects.filter(owner__isnull=True).delete()


def noop_reverse(apps, schema_editor):
    # Data deletion is not reversible.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('schedule', '0011_alter_assignment_end_date_alter_project_color'),
    ]

    operations = [
        migrations.RunPython(clean_orphan_owners, noop_reverse),
        migrations.AlterField(
            model_name='project',
            name='owner',
            field=models.ForeignKey(
                blank=True,
                on_delete=models.CASCADE,
                related_name='projects',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name='assignment',
            name='owner',
            field=models.ForeignKey(
                blank=True,
                on_delete=models.CASCADE,
                related_name='assignments',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
