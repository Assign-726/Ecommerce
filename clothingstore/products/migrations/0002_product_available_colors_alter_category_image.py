from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='category',
            name='image',
            field=models.ImageField(blank=False, null=True, upload_to='categories/'),
        ),
        migrations.AddField(
            model_name='product',
            name='available_colors',
            field=models.JSONField(blank=True, default=list, help_text='List of available colors for this product'),
        ),
    ]
