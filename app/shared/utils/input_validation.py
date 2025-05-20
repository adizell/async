# app/shared/utils/input_validation.py

import regex
import re
from typing import Optional, Tuple, List, Dict, Any
from app.shared.utils.messages_utils import get_message


class InputValidator:
    """
    Classe para validação e sanitização de entradas de usuário.

    Utiliza expressões regulares para validar nomes, e-mails, slugs e strings genéricas,
    além de verificar a força de senhas e validar dicionários baseados em regras configuráveis.
    """

    # ─────────────────────────────────────────────────────────────
    # Constantes de limites
    MAX_NAME_LENGTH = 100
    MAX_PASSWORD_LENGTH = 72  # Limite seguro para hashing de senha (ex: bcrypt)
    MIN_PASSWORD_LENGTH = 8
    MAX_EMAIL_LENGTH = 255
    MAX_STRING_INPUT_LENGTH = 1000

    # ─────────────────────────────────────────────────────────────
    # Expressões Regulares para validações

    # Nome (NAME_PATTERN):
    # - \p{L}: qualquer letra (de qualquer idioma)
    # - \p{M}: marcas de acento (acentos combinados)
    # - 0-9: números opcionais
    # - Espaço ( ), ponto (.), hífen (-) e apóstrofo (') permitidos
    # - +: um ou mais caracteres
    # - flags=regex.UNICODE: suporte completo a Unicode
    NAME_PATTERN = regex.compile(
        r"^[\p{L}\p{M}0-9 .'-]+$",
        flags=regex.UNICODE
    )

    # E-mail (EMAIL_PATTERN):
    # - Aceita letras, números, pontos, underlines, hífens no usuário
    # - Aceita domínios com letras, números, pontos e hífens
    EMAIL_PATTERN = re.compile(
        r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    )

    # Slug (SLUG_PATTERN):
    # - Apenas letras minúsculas (a-z), números (0-9) e hífens (-)
    SLUG_PATTERN = re.compile(
        r"^[a-z0-9-]+$"
    )

    # Caracteres perigosos para sanitização (DANGEROUS_CHARS):
    # - Usado para impedir injeções e XSS em campos genéricos
    DANGEROUS_CHARS = re.compile(
        r"[<>'\";%{}\[\]]"
    )

    # Caracteres especiais permitidos em senhas
    SPECIAL_CHARACTERS = "!@#$%^&*()_+-=[]{}|;:,.<>?/"

    # ─────────────────────────────────────────────────────────────

    @classmethod
    def validate_password(cls, password: str, language: str = "pt") -> Tuple[bool, Optional[List[str]]]:
        """
        Valida uma senha de acordo com critérios de segurança.

        Returns:
            (bool indicando se é válida, lista de mensagens de erro se inválida)
        """
        errors: List[str] = []

        if not password:
            # ou crie uma mensagem "password_empty" em MESSAGES, ou use "password_empty" que já existe
            errors.append(get_message("password_empty", language))
        else:
            if len(password) < cls.MIN_PASSWORD_LENGTH:
                errors.append(
                    get_message("password_too_short", language, min=cls.MIN_PASSWORD_LENGTH)
                )
            if len(password) > cls.MAX_PASSWORD_LENGTH:
                errors.append(
                    get_message("password_too_long", language, max=cls.MAX_PASSWORD_LENGTH)
                )
            if not any(c.isupper() for c in password):
                errors.append(get_message("password_missing_uppercase", language))
            if not any(c.islower() for c in password):
                errors.append(get_message("password_missing_lowercase", language))
            if not any(c.isdigit() for c in password):
                errors.append(get_message("password_missing_number", language))
            if not any(c in cls.SPECIAL_CHARACTERS for c in password):
                errors.append(get_message("password_missing_special", language))

        if errors:
            return False, errors

        return True, None

    @classmethod
    def sanitize_name(cls, name: str) -> str:
        sanitized = re.sub(r'\s+', ' ', name.strip())
        return sanitized[:cls.MAX_NAME_LENGTH]

    @classmethod
    def validate_email(cls, email: str, language: str = "pt") -> Tuple[bool, Optional[str]]:
        if not email:
            return False, get_message("email_required", language)

        if len(email) > cls.MAX_EMAIL_LENGTH:
            return False, get_message("email_too_long", language, max=cls.MAX_EMAIL_LENGTH)

        if not cls.EMAIL_PATTERN.match(email):
            return False, get_message("email_invalid", language)

        return True, None

    @classmethod
    def validate_slug(cls, slug: str, language: str = "pt") -> Tuple[bool, Optional[str]]:
        if not slug:
            return False, get_message("slug_required", language)

        if not cls.SLUG_PATTERN.match(slug):
            return False, get_message("slug_invalid", language)

        return True, None

    @classmethod
    def sanitize_string(cls, text: str, max_length: Optional[int] = None) -> str:
        if not max_length:
            max_length = cls.MAX_STRING_INPUT_LENGTH

        sanitized = text.strip()
        return sanitized[:max_length]

    @classmethod
    def validate_dict_data(cls, data: Dict[str, Any], rules: Dict[str, Dict[str, Any]], language: str = "pt") -> List[
        str]:
        errors = []

        for field, rule in rules.items():
            if rule.get('required', False) and (field not in data or data[field] is None):
                errors.append(get_message("field_required", language, field=field))
                continue

            if field not in data or data[field] is None:
                continue

            value = data[field]

            expected_type = rule.get('type')
            if expected_type and not isinstance(value, expected_type):
                errors.append(get_message("field_invalid_type", language, field=field, type=expected_type.__name__))
                continue

            if isinstance(value, str):
                max_length = rule.get('max_length', cls.MAX_STRING_INPUT_LENGTH)
                if len(value) > max_length:
                    errors.append(get_message("field_too_long", language, field=field, max=max_length))

                min_length = rule.get('min_length', 0)
                if len(value) < min_length:
                    errors.append(get_message("field_too_short", language, field=field, min=min_length))

                # Padrão regex
                pattern = rule.get('pattern')
                if pattern and not pattern.match(value):
                    errors.append(get_message("field_invalid_format", language, field=field))

                # Verificação de caracteres perigosos
                if rule.get('check_dangerous', False) and cls.DANGEROUS_CHARS.search(value):
                    errors.append(get_message("field_dangerous", language, field=field))

        return errors
