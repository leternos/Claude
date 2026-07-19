#!/usr/bin/env python3
"""Testes de ponta a ponta contra a API simulada (tests/mock_api.py).

Uso: python3 tests/run_tests.py  (a partir de djen-oab-sp/)
"""

import json
import os
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "tests"))

import mock_api  # noqa: E402

FALHAS = []


def verificar(nome, condicao, detalhe=""):
    print(f"  {'ok' if condicao else 'FALHOU'}  {nome}" + (f" — {detalhe}" if not condicao and detalhe else ""))
    if not condicao:
        FALHAS.append(nome)


def main():
    servidor = mock_api.iniciar()
    porta = servidor.server_address[1]
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    os.environ["DJEN_API_BASE"] = f"http://127.0.0.1:{porta}"

    import djen  # importa depois de definir DJEN_API_BASE

    print("1. djen.buscar_comunicacoes (paginação 130 itens em páginas de 100)")
    itens, total = djen.buscar_comunicacoes("123456", "SP", "2026-07-17", "2026-07-17")
    verificar("total reportado = 130", total == 130, f"total={total}")
    verificar("itens coletados = 130", len(itens) == 130, f"len={len(itens)}")
    verificar("processo com máscara", itens[0]["processo"] == "0000001-20.2026.8.26.0100")
    verificar("advogado normalizado", "ADVOGADO TESTE (OAB 123456/SP)" in itens[0]["advogados"])
    verificar("texto sem HTML", "<p>" not in itens[0]["texto"] and "Intime-se" in itens[0]["texto"])

    print("2. busca sem resultados (OAB diferente)")
    vazios, total_vazio = djen.buscar_comunicacoes("999999", "SP", "2026-07-17", "2026-07-17")
    verificar("zero itens", vazios == [] and total_vazio == 0)

    print("3. geradores de exportação")
    csv_txt = djen.gerar_csv(itens)
    verificar("CSV com cabeçalho e 131 linhas",
              csv_txt.count("\r\n") == 131 and csv_txt.lstrip("﻿").startswith('"data"'))
    html_txt = djen.gerar_html(itens, "Teste", "sub")
    verificar("HTML com 130 publicações", html_txt.count('class="pub"') == 130)
    verificar("JSON válido", len(json.loads(djen.gerar_json(itens))) == 130)
    resumo = djen.resumo_texto(itens, "123456", "SP", "2026-07-17", "2026-07-17")
    verificar("resumo cita total", "Total: 130" in resumo)

    print("4. daily_export.py --sem-email (subprocesso)")
    cfg_original = (RAIZ / "config.json").read_text(encoding="utf-8")
    cfg = json.loads(cfg_original)
    cfg["numeroOab"] = "123456"
    (RAIZ / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n",
                                      encoding="utf-8")
    try:
        proc = subprocess.run(
            [sys.executable, "daily_export.py", "--data", "2026-07-17", "--sem-email"],
            cwd=RAIZ, capture_output=True, text=True, timeout=120,
            env={**os.environ, "DJEN_API_BASE": f"http://127.0.0.1:{porta}"})
        verificar("saída 0", proc.returncode == 0, proc.stderr[-400:])
        verificar("resumo no stdout", "Total: 130" in proc.stdout)
        for ext in (".csv", ".html", ".json"):
            arq = RAIZ / "exports" / f"djen_OAB-123456-SP_2026-07-17{ext}"
            verificar(f"gerou {arq.name}", arq.exists() and arq.stat().st_size > 0)
    finally:
        (RAIZ / "config.json").write_text(cfg_original, encoding="utf-8")

    print("5. notificacao.montar_payload_sendgrid (sem rede)")
    import notificacao  # noqa: E402
    cfg_sg = {"provedor": "sendgrid", "para": ["gcforte@me.com", "outro@x.com"],
              "de": "gcforte@me.com", "de_nome": "DJEN"}
    anexo = [notificacao._anexo(RAIZ / "config.json")]
    pl = notificacao.montar_payload_sendgrid(
        cfg_sg, "Assunto", "corpo txt", "<b>html</b>", anexo)
    verificar("2 destinatários", len(pl["personalizations"][0]["to"]) == 2)
    verificar("remetente correto", pl["from"]["email"] == "gcforte@me.com")
    verificar("conteúdo txt+html", [c["type"] for c in pl["content"]]
              == ["text/plain", "text/html"])
    verificar("anexo base64 presente",
              pl["attachments"][0]["filename"] == "config.json"
              and len(pl["attachments"][0]["content"]) > 0)

    print("6. webapp app.py (subprocesso)")
    porta_app = 8899
    app = subprocess.Popen([sys.executable, "app.py", str(porta_app)], cwd=RAIZ,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           env={**os.environ, "DJEN_API_BASE": f"http://127.0.0.1:{porta}"})
    try:
        base = f"http://127.0.0.1:{porta_app}"
        for _ in range(50):
            try:
                urllib.request.urlopen(f"{base}/api/config", timeout=2)
                break
            except OSError:
                time.sleep(0.2)
        pagina = urllib.request.urlopen(f"{base}/", timeout=10).read().decode()
        verificar("página inicial (sem formulário, OAB fixa) carrega",
                  "Publicações da OAB" in pagina and 'data-fmt="csv"' in pagina
                  and 'id="numeroOab"' not in pagina)
        consulta = ("numeroOab=123456&ufOab=SP&dataInicio=2026-07-17"
                    "&dataFim=2026-07-17&siglaTribunal=")
        busca = json.loads(urllib.request.urlopen(
            f"{base}/api/search?{consulta}", timeout=60).read())
        verificar("/api/search retorna 130", len(busca["itens"]) == 130)
        resp_csv = urllib.request.urlopen(
            f"{base}/api/export?{consulta}&formato=csv", timeout=60)
        verificar("/api/export CSV anexa arquivo",
                  "attachment" in resp_csv.headers.get("Content-Disposition", "")
                  and len(resp_csv.read()) > 1000)
        resp_erro = urllib.request.urlopen(f"{base}/api/config", timeout=10)
        verificar("/api/config responde", resp_erro.status == 200)
    finally:
        app.terminate()

    print()
    if FALHAS:
        print(f"{len(FALHAS)} teste(s) falharam: {FALHAS}")
        sys.exit(1)
    print("Todos os testes passaram.")


if __name__ == "__main__":
    main()
