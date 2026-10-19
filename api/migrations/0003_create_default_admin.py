from django.db import migrations
from django.utils import timezone
from django.contrib.auth.hashers import make_password

def create_admin_superuser(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    if not User.objects.filter(username="admin").exists():
        now = timezone.now()
        User.objects.create(
            username="admin",
            email="admin@example.com",
            password=make_password("admin123"),
            is_staff=True,
            is_superuser=True,
            is_active=True,
            date_joined=now,
            last_login=now,
        )

def remove_admin_superuser(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ("api", "0002_airequest_embedding_latency_ms"),
    ]

    operations = [
        migrations.RunPython(create_admin_superuser, reverse_code=remove_admin_superuser),
    ]
