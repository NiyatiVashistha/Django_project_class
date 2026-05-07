from courses.models import SiteConfiguration

def site_config(request):
    """
    Makes site configuration globally available in templates.
    Gracefully handles missing tables (before migrations).
    """
    from django.db import OperationalError, ProgrammingError
    try:
        config = SiteConfiguration.objects.first()
    except (OperationalError, ProgrammingError):
        config = None

    if not config:
        # Provide sensible defaults if no config exists yet
        return {
            'site_config': {
                'site_name': 'Academic LMS',
                'primary_color': '#1a73e8',
                'secondary_color': '#202124',
                'hero_title': 'Learn Without Limits',
                'hero_subtitle': 'Start, switch, or advance your career with world-class online courses.',
                'layout_type': 'classic',
            }
        }
    # Cart Count logic (Session-based)
    cart = request.session.get('cart', {})
    cart_count = sum(cart.values()) if isinstance(cart, dict) else 0

    return {
        'site_config': config,
        'cart_count': cart_count
    }
