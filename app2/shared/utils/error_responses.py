# app/shared/utils/error_responses.py

# Respostas de erro genéricas
common_errors = {
    500: {
        "description": "Internal server error",
        "content": {
            "application/json": {
                "example": {
                    "detail": "Internal server error."
                }
            }
        }
    }
}

# Erros para autenticação e registro de usuário
auth_errors = {
    400: {
        "description": "Bad Request (ex: token inválido para logout)",
        "content": {
            "application/json": {
                "example": {
                    "detail": "Token does not support revocation."
                }
            }
        }
    },
    401: {
        "description": "Unauthorized (Invalid credentials or token)",
        "content": {
            "application/json": {
                "examples": {
                    "invalid_token": {
                        "summary": "Invalid Token",
                        "value": {"detail": "Invalid token."}
                    },
                    "invalid_credentials": {
                        "summary": "Invalid Credentials",
                        "value": {"detail": "Invalid email or password."}
                    },
                    "inactive_user": {
                        "summary": "Inactive User",
                        "value": {"detail": "Inactive user account. Contact the administrator."}
                    }
                }
            }
        }
    },
    409: {
        "description": "Conflict (Email already in use)",
        "content": {
            "application/json": {
                "example": {
                    "detail": "User with email 'user@example.com' already exists."
                }
            }
        }
    },
    **common_errors
}

# Erros para usuários (administração, update, delete)
user_errors = {
    400: {
        "description": "Bad Request",
        "content": {
            "application/json": {
                "examples": {
                    "self_deactivation": {
                        "summary": "Self Deactivation Not Allowed",
                        "value": {"detail": "You cannot deactivate your own user."}
                    },
                    "delete_without_confirmation": {
                        "summary": "Delete Without Confirmation",
                        "value": {
                            "detail": "Permanent deletion requires explicit confirmation. Add ?confirm=true to the URL."}
                    }
                }
            }
        }
    },
    403: {
        "description": "Forbidden (Not a superuser)",
        "content": {
            "application/json": {
                "example": {
                    "detail": "User does not have permission."
                }
            }
        }
    },
    404: {
        "description": "User not found",
        "content": {
            "application/json": {
                "example": {
                    "detail": "User not found."
                }
            }
        }
    },
    422: {
        "description": "Validation Error",
        "content": {
            "application/json": {
                "example": {
                    "detail": "Password must have at least 8 characters."
                }
            }
        }
    },
    **common_errors
}
