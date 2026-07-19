#!/usr/bin/env python3
"""Exportação diária do DJEN: busca as publicações do dia para a OAB configurada,
salva CSV/HTML/JSON em exports/ e envia o resultado por e-mail.

Uso:
  python3 daily_export.py                 # publicações de hoje (horário de Brasília)
  python3 daily_export.py --data 2026-07-17
  python3 daily_export.py --sem-email     # só gera os arquivos

A credencial do provedor de e-mail vem de variável de ambiente ou arquivo:
  SMTP     → DJEN_SMTP_SENHA   ou .smtp_senha   (iCloud/Gmail: senha de aplicativo)
  SendGrid → SENDGRID_API_KEY  ou .sendgrid_key
O provedor é escolhido em config.json → email.provedor ("smtp" | "sendgrid").
"""

import argparse
import json
import sys
from pathlib import Path

import djen
import notificacao

RAIZ = Path(__file__).resolve().parent
CONFIG = RAIZ / "config.json"
EXPORTS = RAIZ / "exports"


def carregar_config() -> dict:
    with open(CONFIG, encoding="utf-8") as f:
        return json.load(f)


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
    corpo_html = djen.gerar_html(
        itens, f"DJEN — OAB {numero_oab}/{uf_oab} — {data}",
        f"{len(itens)} publicação(ões) disponibilizada(s) em {data}")
    arq_csv.write_text(djen.gerar_csv(itens), encoding="utf-8")
    arq_html.write_text(corpo_html, encoding="utf-8")
    arq_json.write_text(djen.gerar_json(itens), encoding="utf-8")

    resumo = djen.resumo_texto(itens, numero_oab, uf_oab, data, data)
    print(resumo)
    print(f"Arquivos gerados em {EXPORTS}/:")
    for p in (arq_csv, arq_html, arq_json):
        print(f"  - {p.name}")

    if args.sem_email:
        return

    # E-mail (provedor: smtp ou sendgrid)
    cfg_email = cfg.get("email", {})
    if cfg_email.get("habilitado", False):
        if itens or cfg_email.get("enviar_quando_vazio", True):
            assunto = (f"DJEN OAB {numero_oab}/{uf_oab} — {len(itens)} "
                       f"publicação(ões) em {data}")
            notificacao.enviar(cfg_email, assunto, resumo, corpo_html,
                               [arq_csv, arq_html])
            print(f"E-mail enviado ({cfg_email.get('provedor', 'smtp')}) para "
                  f"{', '.join(cfg_email['para'])}.")
        else:
            print("Nenhuma publicação e 'enviar_quando_vazio' desativado — "
                  "e-mail não enviado.")

    # Alerta curto por WhatsApp (Twilio), opcional
    cfg_wpp = cfg.get("whatsapp", {})
    if cfg_wpp.get("habilitado", False) and cfg_wpp.get("para"):
        if itens or cfg_wpp.get("enviar_quando_vazio", False):
            texto = (f"DJEN OAB {numero_oab}/{uf_oab}: {len(itens)} publicação(ões) "
                     f"em {data}. Detalhes completos no e-mail.")
            try:
                n = notificacao.enviar_whatsapp(cfg_wpp, texto)
                print(f"WhatsApp enviado para {n} número(s).")
            except Exception as e:  # não bloqueia se o e-mail já saiu # noqa: BLE001
                print(f"WhatsApp não enviado: {e}", file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except djen.DJENError as e:
        print(f"ERRO: {e}", file=sys.stderr)
        sys.exit(1)
