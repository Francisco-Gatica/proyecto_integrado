from django import template
from clinica_dental.validators import mostrar_telefono

register = template.Library()


@register.filter(name="formato_telefono")
def formato_telefono(valor):
    """
    Formatea un teléfono para mostrarlo como '+56 9 1111 1111'.
    """
    return mostrar_telefono(valor)
