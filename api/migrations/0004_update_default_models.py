from django.db import migrations

def update_model_configs(apps, schema_editor):
    AIModelConfig = apps.get_model('api', 'AIModelConfig')
    AIModelConfig.objects.all().update(primary_model="gemini-3.5-flash-lite", backup_model="gemini-3.5-flash-lite")

def reverse_update(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ("api", "0003_create_default_admin"),
    ]

    operations = [
        migrations.RunPython(update_model_configs, reverse_code=reverse_update),
    ]
