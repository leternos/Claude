#!/usr/bin/env python3
"""Gera o relatório HTML das publicações do DJEN para a OAB do config.json.

Sem perguntas, sem formulário: usa a OAB configurada e o dia de hoje (Brasília).
Escreve exports/relatorio_<data>.html e abre no navegador padrão.

Uso:
  python3 relatorio.py                 # publicações de hoje
  python3 relatorio.py --data 2026-07-17
  python3 relatorio.py --nao-abrir     # só gera o arquivo, não abre o navegador
  python3 relatorio.py --stdout        # imprime o HTML na saída padrão
"""

import argparse
import json
import sys
import webbrowser
from pathlib import Path

import djen

RAIZ = Path(__file__).resolve().parent
CONFIG = RAIZ / "config.json"
EXPORTS = RAIZ / "exports"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", help="Data AAAA-MM-DD (padrão: hoje)")
    parser.add_argument("--nao-abrir", action="store_true", help="Não abre o navegador")
    parser.add_argument("--stdout", action="store_true", help="Imprime o HTML no stdout")
    args = parser.parse_args()

    with open(CONFIG, encoding="utf-8") as f:
        cfg = json.load(f)
    oab = str(cfg.get("numeroOab", "")).strip()
    uf = cfg.get("ufOab", "SP")
    if not oab:
        raise SystemExit("Configure 'numeroOab' em config.json antes de gerar o relatório.")

    data = args.data or djen.hoje_brasilia().isoformat()
    itens, _ = djen.buscar_comunicacoes(
        numero_oab=oab, uf_oab=uf, data_inicio=data, data_fim=data,
        sigla_tribunal=cfg.get("siglaTribunal", ""))
    html = djen.gerar_html(
        itens, f"DJEN — OAB {oab}/{uf} — {data}",
        f"{len(itens)} publicação(ões) disponibilizada(s) em {data}")

    if args.stdout:
        sys.stdout.write(html)
        return

    EXPORTS.mkdir(exist_ok=True)
    arquivo = EXPORTS / f"relatorio_OAB-{oab}-{uf}_{data}.html"
    arquivo.write_text(html, encoding="utf-8")
    print(f"{len(itens)} publicação(ões) em {data}. Relatório: {arquivo}")
    if not args.nao_abrir:
        webbrowser.open(arquivo.as_uri())


if __name__ == "__main__":
    try:
        main()
    except djen.DJENError as e:
        print(f"ERRO: {e}", file=sys.stderr)
        sys.exit(1)
