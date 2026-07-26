#!/usr/bin/env python3
"""Monta o JSON de --environment da Lambda a partir de variáveis já exportadas
no shell (evita problemas de aspas/espaços ao montar isso à mão no bash)."""

import json
import os

CHAVES = [
    "NUMERO_OAB", "UF_OAB", "NOME_ADVOGADO", "SIGLA_TRIBUNAL",
    "EMAIL_HABILITADO", "EMAIL_PROVEDOR", "EMAIL_PARA", "EMAIL_DE", "EMAIL_DE_NOME",
    "SMTP_HOST", "SMTP_PORTA", "SMTP_USUARIO", "ENVIAR_QUANDO_VAZIO",
    "WHATSAPP_HABILITADO", "WHATSAPP_DE", "WHATSAPP_PARA", "WHATSAPP_ENVIAR_QUANDO_VAZIO",
    "SENDGRID_API_KEY", "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "DJEN_SMTP_SENHA",
]

variaveis = {chave: os.environ[chave] for chave in CHAVES if os.environ.get(chave)}
print(json.dumps({"Variables": variaveis}))
