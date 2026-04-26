from django.utils.text import slugify


def generate_unique_slug(model_class, title, slug_field="slug"):
    """
    Generate a unique slug for a model based on title.
    """
    base_slug = slugify(title)
    slug = base_slug
    counter = 1

    while model_class.objects.filter(**{slug_field: slug}).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    return slug