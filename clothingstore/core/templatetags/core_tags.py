from django import template
from products.models import Category

register = template.Library()

@register.simple_tag
def get_categories():
    """Get all active categories for navigation"""
    return Category.objects.filter(is_active=True)[:6]

@register.inclusion_tag('core/breadcrumbs.html')
def breadcrumbs(current_page, category=None):
    """Generate breadcrumbs for navigation"""
    breadcrumb_list = [{'name': 'Home', 'url': '/'}]
    
    if category:
        breadcrumb_list.append({
            'name': 'Products', 
            'url': '/products/'
        })
        breadcrumb_list.append({
            'name': category.name,
            'url': f'/products/?category={category.slug}'
        })
    elif current_page == 'products':
        breadcrumb_list.append({
            'name': 'Products',
            'url': '/products/'
        })
    
    return {'breadcrumbs': breadcrumb_list}

@register.filter
def currency(value):
    """Format price as currency"""
    try:
        return f"${float(value):.2f}"
    except (ValueError, TypeError):
        return f"${0:.2f}"
