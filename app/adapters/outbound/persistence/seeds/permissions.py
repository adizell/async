# app/adapters/outbound/persistence/seeds/permissions.py

"""
Script de seed para permissões e grupos de acesso.
"""

import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.adapters.configuration.config import settings
from app.adapters.outbound.persistence.models.user_group.auth_group import AuthGroup
from app.adapters.outbound.persistence.models.user_group.auth_permission import AuthPermission
from app.adapters.outbound.persistence.models.user_group.auth_content_type import AuthContentType

logger = logging.getLogger(__name__)

# Grupos existentes
groups = ["admin", "user", "owner", "visitor"]

# Permissões que o sistema reconhece
content_types = [
    {"app_label": "user", "model": "register_user"},
    {"app_label": "user", "model": "login_user"},
    {"app_label": "user", "model": "list_users"},
]

# Distribuição de permissões por grupo
group_permissions = {
    "admin": [
        "register_user",
        "login_user",
        "list_users",
    ],
    "owner": [
        "register_user",
        "login_user",
        "list_users",
    ],
    "user": [
        "login_user",
    ],
    "visitor": [
        "login_user",
    ]
}

# Constrói a URL síncrona para o SQLAlchemy
SYNC_DB_URL = str(settings.DATABASE_URL).replace("asyncpg", "psycopg2")
engine = create_engine(SYNC_DB_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def run_permissions_seed():
    session = SessionLocal()
    try:
        # Criar ou recuperar grupos
        group_objs = {}
        for name in groups:
            group = session.query(AuthGroup).filter_by(name=name).first()
            if not group:
                group = AuthGroup(name=name)
                session.add(group)
                logger.info(f"🟢 Grupo '{name}' criado.")
            else:
                logger.info(f"🟡 Grupo '{name}' já existe.")
            group_objs[name] = group

        # Criar ou recuperar content types e permissões
        permission_objs = {}
        for ct in content_types:
            ct_obj = session.query(AuthContentType) \
                .filter_by(app_label=ct["app_label"], model=ct["model"]) \
                .first()
            if not ct_obj:
                ct_obj = AuthContentType(**ct)
                session.add(ct_obj)
                session.flush()
                logger.info(f"🟢 ContentType '{ct['app_label']}.{ct['model']}' criado.")
            else:
                logger.info(f"🟡 ContentType '{ct['app_label']}.{ct['model']}' já existe.")

            perm = session.query(AuthPermission) \
                .filter_by(codename=ct["model"]) \
                .first()
            if not perm:
                perm = AuthPermission(
                    name=f"Can {ct['model']}",
                    codename=ct["model"],
                    content_type_id=ct_obj.id,
                )
                session.add(perm)
                session.flush()
                logger.info(f"🟢 Permissão '{ct['model']}' criada.")
            else:
                logger.info(f"🟡 Permissão '{ct['model']}' já existe.")

            permission_objs[ct["model"]] = perm

        # Atribuir permissões aos grupos
        for group_name, perms in group_permissions.items():
            group = group_objs[group_name]
            for codename in perms:
                perm = permission_objs.get(codename)
                if perm and perm not in group.permissions:
                    group.permissions.append(perm)
                    logger.info(f"🟢 Permissão '{codename}' adicionada ao grupo '{group_name}'.")
                elif perm:
                    logger.info(f"🟡 Grupo '{group_name}' já possui '{codename}'.")

        session.commit()
        logger.info("✅ Seed de permissões finalizado com sucesso.")

    except Exception as e:
        session.rollback()
        logger.error(f"🔴 Erro ao executar seed: {e}")
        raise

    finally:
        session.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_permissions_seed()
