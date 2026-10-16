from django.db import migrations, models


def rellenar(apps, schema_editor):
    """Las grabaciones ya procesadas toman el dato de su JSON."""
    Grabacion = apps.get_model("grabaciones", "Grabacion")
    for g in Grabacion.objects.filter(estado="procesada").exclude(resultado=None):
        g.n_canales_buenos = g.resultado.get("metadatos", {}).get("n_canales_buenos")
        g.save(update_fields=["n_canales_buenos"])


class Migration(migrations.Migration):

    dependencies = [
        ('grabaciones', '0002_procesador'),
    ]

    operations = [
        migrations.AddField(
            model_name='grabacion',
            name='n_canales_buenos',
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.RunPython(rellenar, migrations.RunPython.noop),
    ]
