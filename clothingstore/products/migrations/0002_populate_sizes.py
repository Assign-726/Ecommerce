from django.db import migrations

def create_shoe_sizes(apps, schema_editor):
    Size = apps.get_model('products', 'Size')
    
    # Add shoe sizes
    shoe_sizes = [
        ('5', 'US 5'), ('5.5', 'US 5.5'),
        ('6', 'US 6'), ('6.5', 'US 6.5'),
        ('7', 'US 7'), ('7.5', 'US 7.5'),
        ('8', 'US 8'), ('8.5', 'US 8.5'),
        ('9', 'US 9'), ('9.5', 'US 9.5'),
        ('10', 'US 10'), ('10.5', 'US 10.5'),
        ('11', 'US 11'), ('11.5', 'US 11.5'),
        ('12', 'US 12'), ('12.5', 'US 12.5'),
        ('13', 'US 13'),
    ]
    
    for order, (name, display_name) in enumerate(shoe_sizes, start=1):
        Size.objects.get_or_create(
            name=name,
            defaults={
                'display_name': display_name,
                'size_type': 'shoes',
                'order': order,
                'is_active': True
            }
        )

class Migration(migrations.Migration):

    dependencies = [
        ('products', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_shoe_sizes),
    ]
