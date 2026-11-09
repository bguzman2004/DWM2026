import re

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE = re.compile(r"^(?:\+?56)?(9\d{8})$")


def clean_email(value):
    if value is None:
        return None
    value = value.strip()
    if not EMAIL.match(value):
        raise ValueError("correo invalido")
    return value.lower()


def clean_phone(value):
    if value is None:
        return None
    found = PHONE.match(re.sub(r"\s", "", value))
    if not found:
        raise ValueError("telefono invalido: debe ser un celular chileno, por ejemplo 912345678")
    return "+56" + found.group(1)


def clean_name(value):
    if value is None:
        return None
    value = " ".join(value.split())
    if len(value) < 3:
        raise ValueError("el nombre debe tener al menos 3 caracteres")
    return value
