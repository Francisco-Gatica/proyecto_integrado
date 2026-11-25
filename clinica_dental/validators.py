import datetime
import re

RUT_REGEX = re.compile(r"^(\d{7,8})-([\dkK])$")
TELEFONO_CL_REGEX = re.compile(r"^(?:\+?56)?(9\d{8})$")


def parsear_fecha(valor, obligatorio=False):
    """
    Convierte una fecha en formato DD/MM/YYYY (o YYYY-MM-DD por compatibilidad) a datetime.date.
    """
    texto = (valor or "").strip()
    if not texto:
        if obligatorio:
            raise ValueError("La fecha es obligatoria.")
        return None

    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(texto, fmt).date()
        except ValueError:
            continue

    raise ValueError("Formato de fecha inválido (debe ser DD/MM/YYYY).")


def formatear_fecha(fecha):
    """
    Formatea una fecha a DD/MM/YYYY.
    """
    if not fecha:
        return ""
    if hasattr(fecha, "strftime"):
        return fecha.strftime("%d/%m/%Y")
    return str(fecha)


def validar_rut(rut):
    """
    Valida que el RUT tenga formato 11111111-1 (7 u 8 dígitos, guión y dígito verificador 0-9 o K).
    """
    texto = (rut or "").strip()
    if not texto:
        return None

    match = RUT_REGEX.match(texto)
    if not match:
        raise ValueError("El RUT debe ingresarse con formato 11111111-1 (sin puntos y con guión).")

    cuerpo, dv = match.groups()
    return f"{cuerpo}-{dv.upper()}"


def formatear_telefono_cl(telefono):
    """
    Valida un teléfono móvil chileno y lo formatea como '+56 9 1111 1111'.
    Acepta variantes con o sin espacios/+56 (ej: '+56 9 1111 1111', '+56911111111', '56911111111', '911111111').
    """
    texto = (telefono or "").strip()
    if not texto:
        return None

    compacto = re.sub(r"[\s\-()]+", "", texto)
    match = TELEFONO_CL_REGEX.match(compacto)
    if not match:
        raise ValueError("El teléfono debe tener formato chileno válido: +56 9 1111 1111.")

    numero_local = match.group(1)  # 9XXXXXXXX
    return f"+56 {numero_local[0]} {numero_local[1:5]} {numero_local[5:9]}"


def mostrar_telefono(telefono):
    """
    Devuelve el teléfono formateado como '+56 9 1111 1111' si coincide con un móvil chileno;
    en caso contrario retorna el valor original.
    """
    if not telefono:
        return ""
    try:
        return formatear_telefono_cl(telefono)
    except ValueError:
        return telefono
