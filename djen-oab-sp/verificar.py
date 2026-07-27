#!/usr/bin/env python3
"""Autoteste do ambiente: confirma se esta máquina está pronta para rodar o DJEN.

Verifica versão do Python, a configuração (OAB, nome, e-mail), a presença das
credenciais e — o mais importante — se o IP desta máquina tem acesso à API do
CNJ (que bloqueia acessos de fora do Brasil).

Uso:  python3 verificar.py
"""

import json
import os
import sys
import urllib.parse
from pathlib import Path

import djen

RAIZ = Path(__file__).resolve().parent
CONFIG = RAIZ / "config.json"

OK, FALHA, AVISO = "\033[32m[OK]\033[0m", "\033[31m[X]\033[0m", "\033[33m[!]\033[0m"
if not sys.stdout.isatty():
    OK, FALHA, AVISO = "[OK]", "[X]", "[!]"

pendencias = []


def linha(marca, texto, dica=""):
    print(f" {marca} {texto}")
    if dica:
        print(f"       -> {dica}")


def tem_credencial(variaveis, arquivo):
    if any(os.environ.get(v) for v in variaveis):
        return True
    return (RAIZ / arquivo).exists()


def main():
    print("Verificacao do DJEN OAB/SP")
    print("=" * 42)

    # 1. Python
    v = sys.version_info
    if v >= (3, 9):
        linha(OK, f"Python {v.major}.{v.minor} (>= 3.9)")
    else:
        linha(FALHA, f"Python {v.major}.{v.minor} — precisa de 3.9+")
        pendencias.append("atualizar o Python")

    # 2. Config
    try:
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        linha(FALHA, f"config.json ilegível: {e}")
        print("\nCorrija o config.json antes de continuar.")
        sys.exit(1)

    oab = str(cfg.get("numeroOab", "")).strip()
    uf = cfg.get("ufOab", "SP")
    if oab:
        linha(OK, f"OAB configurada: {oab}/{uf}")
    else:
        linha(FALHA, "OAB não configurada", "preencha 'numeroOab' no config.json")
        pendencias.append("configurar a OAB")

    nome = str(cfg.get("nomeAdvogado", "")).strip()
    linha(OK if nome else AVISO,
          f"Nome do advogado: {nome}" if nome else "Nome do advogado não definido",
          "" if nome else "opcional: preencha 'nomeAdvogado' no config.json")

    # 3. E-mail
    cfg_email = cfg.get("email", {})
    provedor = (cfg_email.get("provedor") or "smtp").lower()
    if not cfg_email.get("habilitado", False):
        linha(AVISO, "E-mail desabilitado (email.habilitado = false)")
    elif provedor == "sendgrid":
        if tem_credencial(("SENDGRID_API_KEY", "DJEN_SENDGRID_KEY"), ".sendgrid_key"):
            linha(OK, "E-mail: SendGrid com credencial presente")
        else:
            linha(FALHA, "E-mail: SendGrid sem API key",
                  "defina SENDGRID_API_KEY ou crie o arquivo .sendgrid_key")
            pendencias.append("credencial do SendGrid")
    elif provedor == "smtp":
        if tem_credencial(("DJEN_SMTP_SENHA", "DJEN_SMTP_PASSWORD"), ".smtp_senha"):
            linha(OK, "E-mail: SMTP com senha presente")
        else:
            linha(FALHA, "E-mail: SMTP sem senha",
                  "defina DJEN_SMTP_SENHA ou crie o arquivo .smtp_senha")
            pendencias.append("senha do SMTP")

    # 4. WhatsApp (opcional)
    cfg_wpp = cfg.get("whatsapp", {})
    if cfg_wpp.get("habilitado", False):
        if tem_credencial(("TWILIO_ACCOUNT_SID",), ".twilio_sid") and \
           tem_credencial(("TWILIO_AUTH_TOKEN",), ".twilio_token"):
            linha(OK, "WhatsApp: Twilio com credenciais presentes")
        else:
            linha(FALHA, "WhatsApp habilitado, mas sem credenciais Twilio",
                  "defina TWILIO_ACCOUNT_SID e TWILIO_AUTH_TOKEN")
            pendencias.append("credenciais do Twilio")

    # 5. Conexão com o DJEN (o teste que decide tudo)
    if djen.DJEN_PROXY:
        linha(AVISO, f"DJEN_PROXY ativo: {djen.DJEN_PROXY}")
    if not oab:
        linha(AVISO, "Pulei o teste de conexão (OAB não configurada)")
    else:
        print(f" ... testando conexão com o CNJ para OAB {oab}/{uf} ...")
        data = djen.hoje_brasilia().isoformat()
        params = {"numeroOab": oab, "ufOab": uf, "itensPorPagina": 1, "pagina": 1,
                  "dataDisponibilizacaoInicio": data, "dataDisponibilizacaoFim": data}
        url = f"{djen.API_BASE}{djen.ENDPOINT}?{urllib.parse.urlencode(params)}"
        try:
            dados = djen._requisitar(url)
            total = dados.get("count", dados.get("total", 0))
            linha(OK, f"Conexão com o DJEN OK — {total} publicação(ões) hoje ({data})")
        except djen.GeoBloqueioError:
            linha(FALHA, "Bloqueio geográfico: este IP está FORA do Brasil (HTTP 403)",
                  "rode numa máquina/rede no Brasil, ou configure DJEN_PROXY")
            pendencias.append("acesso a partir de um IP no Brasil")
        except djen.DJENError as e:
            linha(FALHA, f"Falha ao consultar o DJEN: {e}")
            pendencias.append("investigar a conexão com o DJEN")

    # Resumo
    print("=" * 42)
    if not pendencias:
        print("Tudo pronto! Rode:  python3 relatorio.py")
        sys.exit(0)
    print("Pendências antes de rodar com dados reais:")
    for p in pendencias:
        print(f"  - {p}")
    sys.exit(1)


if __name__ == "__main__":
    main()
