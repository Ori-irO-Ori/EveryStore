from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitesettings',
            name='custom_email_template',
            field=models.FileField(
                blank=True,
                help_text='Upload an HTML file to replace the default order confirmation email. Use {{ order }}, {{ store_name }}, {{ primary_color }} as template variables. Delete to revert to the default.',
                null=True,
                upload_to='site/email/',
                verbose_name='Custom order confirmation email (HTML)',
            ),
        ),
    ]
