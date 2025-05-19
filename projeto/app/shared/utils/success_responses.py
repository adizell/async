# app/shared/utils/success_responses.py

# Respostas de sucesso genéricas
common_success = {
    200: {
        "description": "Request processed successfully",
        "content": {
            "application/json": {
                "example": {"message": "Operation completed successfully."}
            }
        }
    }
}

# Sucessos para autenticação e usuários
auth_success = {
    201: {
        "description": "User created successfully",
        "content": {
            "application/json": {
                "example": {
                    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "email": "user@example.com",
                    "is_active": True,
                    "is_superuser": False,
                    "created_at": "2023-01-01T00:00:00.000Z",
                    "updated_at": None
                }
            }
        }
    },
    **common_success
}
