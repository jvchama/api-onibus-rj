import os

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

# O header esperado em todos os requests protegidos
_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Carregadas uma vez na inicialização — vêm do .env via python-dotenv
API_KEY       = os.getenv("API_KEY", "")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")


async def require_api_key(key: str = Security(_header)) -> None:
    """Dependência para endpoints de usuário: POST e DELETE /registrations.

    Retorna 503 se a chave não estiver configurada no servidor (ajuda a
    detectar .env incompleto em vez de silenciosamente aceitar qualquer coisa).
    Retorna 403 para chave ausente ou incorreta.
    """
    if not API_KEY:
        raise HTTPException(503, detail="API_KEY não configurada no servidor")
    if key != API_KEY:
        raise HTTPException(403, detail="API key inválida ou ausente")


async def require_admin_key(key: str = Security(_header)) -> None:
    """Dependência para endpoints administrativos: GET /registrations.

    Chave separada da API_KEY para limitar o impacto de um vazamento —
    comprometer a ADMIN_KEY não expõe a chave usada pelo frontend e vice-versa.
    """
    if not ADMIN_API_KEY:
        raise HTTPException(503, detail="ADMIN_API_KEY não configurada no servidor")
    if key != ADMIN_API_KEY:
        raise HTTPException(403, detail="Admin key inválida ou ausente")
