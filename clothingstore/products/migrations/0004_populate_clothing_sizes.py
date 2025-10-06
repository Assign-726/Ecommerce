from django.db import migrations


def create_clothing_sizes(apps, schema_editor):
    Size = apps.get_model('products', 'Size')
    clothing_sizes = [
        ('XS', 'Extra Small', 1),
        ('S', 'Small', 2),
        ('M', 'Medium', 3),
        ('L', 'Large', 4),
        ('XL', 'Extra Large', 5),
        ('XXL', 'Double Extra Large', 6),
        ('XXXL', 'Triple Extra Large', 7),
    ]
    for name, display, order in clothing_sizes:
        Size.objects.get_or_create(
            name=name,
            defaults={
                'display_name': display,
                'size_type': 'clothing',
                'order': order,
                'is_active': True,
            },
        )


def delete_clothing_sizes(apps, schema_editor):
    Size = apps.get_model('products', 'Size')
    Size.objects.filter(name__in=['XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0003_merge_20250822_1406'),
    ]

    operations = [
        migrations.RunPython(create_clothing_sizes, delete_clothing_sizes),
    ]
