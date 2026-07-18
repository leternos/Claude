#!/usr/bin/env python3
"""Exportação diária do DJEN: busca as publicações do dia para a OAB configurada,
salva CSV/HTML/JSON em exports/ e envia o resultado por e-mail.

Uso:
  python3 daily_export.py                 # publicações de hoje (horário de Brasília)
  python3 daily_export.py --data 2026-07-17
  python3 daily_export.py --sem-email     # só gera os arquivos

A senha do SMTP vem da variável de ambiente DJEN_SMTP_SENHA
(para iCloud/Gmail, use uma senha de aplicativo, não a senha da conta).
"""

import argparse
import json
import os
import smtplib
import sys
from email.message import EmailMessage
from pathlib import Path

import djen

RAIZ = Path(__file__).resolve().parent
CONFIG = RAIZ / "config.json"
EXPORTS = RAIZ / "exports"


def carregar_config() -> dict:
    with open(CONFIG, encoding="utf-8") as f:
        return json.load(f)


def enviar_email(cfg_email: dict, assunto: str, corpo: str, anexos: list):
    senha = os.environ.get("DJEN_SMTP_SENHA") or os.environ.get("DJEN_SMTP_PASSWORD")
    arquivo_senha = RAIZ / ".smtp_senha"
    if not senha and arquivo_senha.exists():
        senha = arquivo_senha.read_text(encoding="utf-8").strip()
    if not senha:
        raise SystemExit("Defina a variável de ambiente DJEN_SMTP_SENHA ou crie o arquivo "
                         f"{arquivo_senha} com a senha de aplicativo do SMTP "
                         "(ou rode com --sem-email).")
    msg = EmailMessage()
    msg["Subject"] = assunto
    msg["From"] = cfg_email["de"]
    msg["To"] = ", ".join(cfg_email["para"])
    msg.set_content(corpo)
    for caminho in anexos:
        subtipo = {"csv": "csv", "html": "html", "json": "json"}.get(
            caminho.suffix.lstrip("."), "octet-stream")
        msg.add_attachment(caminho.read_bytes(), maintype="text", subtype=subtipo,
                           filename=caminho.name)
    with smtplib.SMTP(cfg_email["smtp_host"], int(cfg_email.get("smtp_porta", 587)),
                      timeout=60) as smtp:
        smtp.starttls()
        smtp.login(cfg_email.get("smtp_usuario") or cfg_email["de"], senha)
        smtp.send_message(msg)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", help="Data no formato AAAA-MM-DD (padrão: hoje)")
    parser.add_argument("--sem-email", action="store_true",
                        help="Não envia e-mail, só gera os arquivos")
    args = parser.parse_args()

    cfg = carregar_config()
    numero_oab = str(cfg.get("numeroOab", "")).strip()
    uf_oab = cfg.get("ufOab", "SP")
    if not numero_oab:
        raise SystemExit("Configure 'numeroOab' em config.json (ou pela interface web) "
                         "antes de rodar a exportação diária.")

    data = args.data or djen.hoje_brasilia().isoformat()
    print(f"Buscando publicações do DJEN para OAB {numero_oab}/{uf_oab} em {data}…")
    itens, total = djen.buscar_comunicacoes(
        numero_oab=numero_oab, uf_oab=uf_oab,
        data_inicio=data, data_fim=data,
        sigla_tribunal=cfg.get("siglaTribunal", ""),
    )

    EXPORTS.mkdir(exist_ok=True)
    base = EXPORTS / f"djen_OAB-{numero_oab}-{uf_oab}_{data}"
    arq_csv = base.with_suffix(".csv")
    arq_html = base.with_suffix(".html")
    arq_json = base.with_suffix(".json")
    arq_csv.write_text(djen.gerar_csv(itens), encoding="utf-8")
    arq_html.write_text(djen.gerar_html(
        itens, f"DJEN — OAB {numero_oab}/{uf_oab} — {data}",
        f"{len(itens)} publicação(ões) disponibilizada(s) em {data}"), encoding="utf-8")
    arq_json.write_text(djen.gerar_json(itens), encoding="utf-8")

    resumo = djen.resumo_texto(itens, numero_oab, uf_oab, data, data)
    print(resumo)
    print(f"Arquivos gerados em {EXPORTS}/:")
    for p in (arq_csv, arq_html, arq_json):
        print(f"  - {p.name}")

    cfg_email = cfg.get("email", {})
    if args.sem_email or not cfg_email.get("habilitado", False):
        return
    if not itens and not cfg_email.get("enviar_quando_vazio", True):
        print("Nenhuma publicação e 'enviar_quando_vazio' desativado — e-mail não enviado.")
        return

    assunto = (f"DJEN OAB {numero_oab}/{uf_oab} — {len(itens)} publicação(ões) "
               f"em {data}")
    enviar_email(cfg_email, assunto, resumo, [arq_csv, arq_html])
    print(f"E-mail enviado para {', '.join(cfg_email['para'])}.")


if __name__ == "__main__":
    try:
        main()
    except djen.DJENError as e:
        print(f"ERRO: {e}", file=sys.stderr)
        sys.exit(1)
