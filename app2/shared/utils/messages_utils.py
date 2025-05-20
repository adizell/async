# app/shared/utils/messages_utils.py

"""
Sistema de mensagens multilíngue para validação e feedback da API.

Este módulo fornece suporte a tradução de mensagens em diferentes idiomas,
facilitando a internacionalização do sistema (i18n).
"""

from typing import Dict

# Dicionário principal de mensagens
MESSAGES: Dict[str, Dict[str, str]] = {
    # Password validation
    "password_too_short": {
        "pt": "Senha deve ter pelo menos {min} caracteres.",
        "en": "Password must be at least {min} characters long."
    },
    "password_too_long": {
        "pt": "Senha é muito longa (máximo {max} caracteres).",
        "en": "Password is too long (maximum {max} characters)."
    },
    "password_missing_uppercase": {
        "pt": "Senha deve conter pelo menos uma letra maiúscula.",
        "en": "Password must contain at least one uppercase letter."
    },
    "password_missing_lowercase": {
        "pt": "Senha deve conter pelo menos uma letra minúscula.",
        "en": "Password must contain at least one lowercase letter."
    },
    "password_missing_number": {
        "pt": "Senha deve conter pelo menos um número.",
        "en": "Password must contain at least one number."
    },
    "password_missing_special": {
        "pt": "Senha deve conter pelo menos um caractere especial (!@#$%^&*).",
        "en": "Password must contain at least one special character (!@#$%^&*)."
    },

    # Email validation
    "email_invalid": {
        "pt": "Formato de e-mail inválido.",
        "en": "Invalid email format."
    },
    "email_too_long": {
        "pt": "E-mail é muito longo (máximo {max} caracteres).",
        "en": "Email is too long (maximum {max} characters)."
    },
    "email_empty": {
        "pt": "E-mail não pode estar vazio.",
        "en": "Email cannot be empty."
    },

    # Slug validation
    "slug_invalid": {
        "pt": "Slug deve conter apenas letras minúsculas, números e hífens.",
        "en": "Slug must contain only lowercase letters, numbers, and hyphens."
    },
    "slug_empty": {
        "pt": "Slug não pode estar vazio.",
        "en": "Slug cannot be empty."
    },

    # Generic fields
    "field_required": {
        "pt": "Campo '{field}' é obrigatório.",
        "en": "Field '{field}' is required."
    },
    "field_invalid_type": {
        "pt": "Campo '{field}' deve ser do tipo {type}.",
        "en": "Field '{field}' must be of type {type}."
    },
    "field_invalid_format": {
        "pt": "Campo '{field}' tem formato inválido.",
        "en": "Field '{field}' has invalid format."
    },
    "field_too_long": {
        "pt": "Campo '{field}' excede o tamanho máximo de {max} caracteres.",
        "en": "Field '{field}' exceeds maximum length of {max} characters."
    },
    "field_too_short": {
        "pt": "Campo '{field}' deve ter pelo menos {min} caracteres.",
        "en": "Field '{field}' must have at least {min} characters."
    },
    "field_dangerous_chars": {
        "pt": "Campo '{field}' contém caracteres não permitidos.",
        "en": "Field '{field}' contains forbidden characters."
    },

    # General
    "generic_invalid_credentials": {
        "pt": "Credenciais inválidas.",
        "en": "Invalid credentials."
    },
    "generic_user_inactive": {
        "pt": "Este usuário está inativo.",
        "en": "This user is inactive."
    },
}


def get_message(key: str, language: str = "pt", **kwargs) -> str:
    """
    Recupera uma mensagem formatada baseada na chave e no idioma.

    Args:
        key (str): Chave da mensagem.
        language (str): Idioma desejado ('pt', 'en', etc).
        kwargs: Variáveis a serem interpoladas na mensagem.

    Returns:
        str: Mensagem finalizada.
    """
    try:
        template = MESSAGES[key][language]
    except KeyError:
        # Tenta usar português como fallback
        template = MESSAGES.get(key, {}).get("pt", f"[Mensagem não encontrada: {key}]")

    return template.format(**kwargs)
