from django import template

register = template.Library()

english_to_bangla_digits = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")

@register.filter
def bangla_number(value):
    """Convert English digits to Bengali digits"""
    try:
        return str(value).translate(english_to_bangla_digits)
    except Exception:
        return value
