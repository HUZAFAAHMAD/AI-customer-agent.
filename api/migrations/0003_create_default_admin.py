from django.db import migrations

def create_admin_superuser(apps, schema_editor):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    if not User.objects.filter(username="admin").exists():
        User.objects.create_superuser("admin", "admin@example.com", "admin123")

def remove_admin_superuser(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ("api", "0002_airequest_embedding_latency_ms"),
    ]

    operations = [
        migrations.RunPython(create_admin_superuser, reverse_code=remove_admin_superuser),
    ]
