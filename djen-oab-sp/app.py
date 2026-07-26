#!/usr/bin/env python3
"""Painel do DJEN para uma OAB fixa (configurada em config.json).

Sem formulário: abre já mostrando as publicações do dia para a OAB configurada.
Uso:  python3 app.py [porta]   (padrão: 8859)  →  http://localhost:8859
"""

import json
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import djen

RAIZ = Path(__file__).resolve().parent
CONFIG = RAIZ / "config.json"
PORTA_PADRAO = 8859

PAGINA = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DJEN — Publicações da OAB</title>
<style>
  :root { --tinta: #1e232b; --papel: #f6f4ef; --cartao: #fff; --borda: #ddd6c8;
          --realce: #8a5a2b; --suave: #5a6472; }
  * { box-sizing: border-box; }
  body { font-family: Georgia, 'Times New Roman', serif; margin: 0;
         background: var(--papel); color: var(--tinta); }
  header.topo { padding: 1.5rem 2rem 1rem; border-bottom: 1px solid var(--borda);
                display: flex; flex-wrap: wrap; align-items: baseline; gap: .5rem 1rem; }
  h1 { margin: 0; font-size: 1.4rem; }
  .oab { color: var(--realce); font-weight: bold; }
  .sub { color: var(--suave); margin: 0; font-size: .9rem; width: 100%; }
  main { max-width: 60rem; margin: 0 auto; padding: 1.25rem 1rem 4rem; }
  .barra { display: flex; flex-wrap: wrap; gap: .6rem; align-items: center;
           margin-bottom: 1rem; }
  .barra input[type=date] { font: inherit; padding: .4rem .55rem;
           border: 1px solid var(--borda); border-radius: 6px; background: #fffdf8; }
  button { font: inherit; padding: .45rem 1rem; border-radius: 6px; cursor: pointer;
           border: 1px solid var(--realce); background: var(--realce); color: #fff; }
  button.secundario { background: transparent; color: var(--realce); }
  button:disabled { opacity: .5; cursor: wait; }
  .empurra { margin-left: auto; }
  #status { margin: .5rem 0 1rem; color: var(--suave); }
  #status.erro { color: #a33; }
  .pub { background: var(--cartao); border: 1px solid var(--borda); border-radius: 10px;
         padding: 1rem 1.25rem; margin-bottom: .9rem; }
  .pub .meta { color: var(--suave); font-size: .85rem; margin-top: .15rem; }
  .pub strong { font-size: 1rem; }
  .num { color: var(--realce); font-weight: bold; margin-right: .5rem; }
  details { margin-top: .5rem; }
  summary { cursor: pointer; color: var(--realce); font-size: .9rem; }
  .texto { border-top: 1px dashed var(--borda); margin-top: .5rem; padding-top: .5rem;
           font-size: .95rem; line-height: 1.55; overflow-wrap: anywhere; }
  a { color: var(--realce); }
  .selo { display: inline-block; background: #efe7d8; border-radius: 999px;
          padding: .1rem .6rem; font-size: .78rem; color: #6b4a1f; margin-left: .4rem; }
  .vazio { color: var(--suave); font-style: italic; }
</style>
</head>
<body>
<header class="topo">
  <h1 id="tituloNome">Publicações do DJEN</h1>
  <p class="sub">OAB <span class="oab" id="tituloOab">…</span> · Diário de Justiça
     Eletrônico Nacional · fonte: API pública comunicaapi.pje.jus.br (CNJ)</p>
</header>
<main>
  <div class="barra">
    <button id="btnAtualizar">Atualizar</button>
    <input type="date" id="data" title="Escolher o dia">
    <span class="empurra"></span>
    <button class="secundario" data-fmt="csv">CSV</button>
    <button class="secundario" data-fmt="html">HTML</button>
    <button class="secundario" data-fmt="json">JSON</button>
  </div>
  <p id="status">Carregando…</p>
  <section id="resultados"></section>
</main>
<script>
const hoje = new Date().toLocaleDateString("sv", {timeZone: "America/Sao_Paulo"});
const inputData = document.getElementById("data");
inputData.value = hoje; inputData.max = hoje;
const status = document.getElementById("status");
const resultados = document.getElementById("resultados");
const esc = s => (s || "").replace(/[&<>"]/g,
  c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

let OAB = "", UF = "SP";
fetch("/api/config").then(r => r.json()).then(cfg => {
  OAB = cfg.numeroOab || ""; UF = cfg.ufOab || "SP";
  document.getElementById("tituloOab").textContent = OAB ? `${OAB}/${UF}` : "(não configurada)";
  if (cfg.nomeAdvogado)
    document.getElementById("tituloNome").textContent =
      `${cfg.nomeAdvogado} — Publicações do DJEN`;
  carregar();
});

async function carregar() {
  const btn = document.getElementById("btnAtualizar");
  btn.disabled = true;
  status.className = "";
  status.textContent = "Consultando o DJEN…";
  resultados.innerHTML = "";
  try {
    const p = new URLSearchParams({dataInicio: inputData.value, dataFim: inputData.value});
    const r = await fetch("/api/search?" + p);
    const dados = await r.json();
    if (!r.ok) throw new Error(dados.erro || "Falha na consulta");
    const n = dados.itens.length;
    status.textContent = `${n} publicação(ões) em ${inputData.value}.`;
    resultados.innerHTML = n ? dados.itens.map((pub, i) => `
      <article class="pub">
        <span class="num">#${i + 1}</span>
        <strong>${esc(pub.processo) || "(processo não informado)"}</strong>
        <span class="selo">${esc(pub.tribunal)}</span>
        <span class="selo">${esc(pub.tipo)}</span>
        ${pub.link ? `<a href="${esc(pub.link)}" target="_blank" rel="noopener">ver no DJEN</a>` : ""}
        <div class="meta">${esc(pub.data)} · ${esc(pub.orgao)} · ${esc(pub.classe)}</div>
        <div class="meta">Partes: ${esc(pub.partes) || "—"}</div>
        <div class="meta">Advogados(as): ${esc(pub.advogados) || "—"}</div>
        <details><summary>Ver inteiro teor</summary>
          <div class="texto">${esc(pub.texto).replace(/\\n/g, "<br>")}</div>
        </details>
      </article>`).join("")
      : '<p class="vazio">Nenhuma publicação nesta data.</p>';
  } catch (e) {
    status.className = "erro";
    status.textContent = "Erro: " + e.message;
  } finally {
    btn.disabled = false;
  }
}

document.getElementById("btnAtualizar").addEventListener("click", carregar);
inputData.addEventListener("change", carregar);
document.querySelectorAll("button[data-fmt]").forEach(btn =>
  btn.addEventListener("click", () => {
    const p = new URLSearchParams({dataInicio: inputData.value, dataFim: inputData.value,
                                   formato: btn.dataset.fmt});
    location.href = "/api/export?" + p;
  }));
</script>
</body>
</html>
"""


def carregar_config() -> dict:
    try:
        with open(CONFIG, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"numeroOab": "", "ufOab": "SP", "siglaTribunal": ""}


class Handler(BaseHTTPRequestHandler):
    server_version = "djen-oab-sp/1.0"

    def _responder(self, corpo: bytes, tipo: str, status: int = 200, download: str = ""):
        self.send_response(status)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        if download:
            self.send_header("Content-Disposition", f'attachment; filename="{download}"')
        self.end_headers()
        self.wfile.write(corpo)

    def _json(self, dados, status: int = 200):
        self._responder(json.dumps(dados, ensure_ascii=False).encode("utf-8"),
                        "application/json; charset=utf-8", status)

    def _buscar(self, q: dict):
        """Usa a OAB do config.json quando não vier na query (padrão do painel)."""
        cfg = carregar_config()
        return djen.buscar_comunicacoes(
            numero_oab=q.get("numeroOab", [cfg.get("numeroOab", "")])[0],
            uf_oab=q.get("ufOab", [cfg.get("ufOab", "SP")])[0],
            data_inicio=q.get("dataInicio", [""])[0] or None,
            data_fim=q.get("dataFim", [""])[0] or None,
            sigla_tribunal=q.get("siglaTribunal", [cfg.get("siglaTribunal", "")])[0],
        )

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(url.query)
        try:
            if url.path == "/":
                self._responder(PAGINA.encode("utf-8"), "text/html; charset=utf-8")
            elif url.path == "/api/config":
                cfg = carregar_config()
                self._json({k: cfg.get(k, "") for k in
                            ("numeroOab", "ufOab", "nomeAdvogado", "siglaTribunal")})
            elif url.path == "/api/search":
                itens, total = self._buscar(q)
                self._json({"total": total, "itens": itens})
            elif url.path == "/api/export":
                itens, _ = self._buscar(q)
                cfg = carregar_config()
                fmt = q.get("formato", ["csv"])[0]
                oab = q.get("numeroOab", [cfg.get("numeroOab", "")])[0]
                uf = q.get("ufOab", [cfg.get("ufOab", "SP")])[0]
                di = q.get("dataInicio", [""])[0] or djen.hoje_brasilia().isoformat()
                df = q.get("dataFim", [""])[0] or di
                nome = f"djen_OAB-{oab}-{uf}_{di}" + ("" if di == df else f"_a_{df}")
                if fmt == "html":
                    corpo = djen.gerar_html(
                        itens, f"DJEN — OAB {oab}/{uf} — {di}" +
                        ("" if di == df else f" a {df}"),
                        f"{len(itens)} publicação(ões)").encode("utf-8")
                    self._responder(corpo, "text/html; charset=utf-8",
                                    download=f"{nome}.html")
                elif fmt == "json":
                    self._responder(djen.gerar_json(itens).encode("utf-8"),
                                    "application/json; charset=utf-8",
                                    download=f"{nome}.json")
                else:
                    self._responder(djen.gerar_csv(itens).encode("utf-8"),
                                    "text/csv; charset=utf-8", download=f"{nome}.csv")
            else:
                self._json({"erro": "Rota não encontrada"}, 404)
        except djen.DJENError as e:
            self._json({"erro": str(e)}, 502)
        except Exception as e:  # noqa: BLE001 — servidor local, erro vai para a UI
            self._json({"erro": f"Erro interno: {e}"}, 500)

    def log_message(self, formato, *args):
        sys.stderr.write(f"[djen-oab-sp] {self.address_string()} {formato % args}\n")


def main():
    porta = int(sys.argv[1]) if len(sys.argv) > 1 else PORTA_PADRAO
    servidor = ThreadingHTTPServer(("127.0.0.1", porta), Handler)
    cfg = carregar_config()
    print(f"DJEN OAB {cfg.get('numeroOab') or '(configure em config.json)'}/"
          f"{cfg.get('ufOab', 'SP')} no ar: http://localhost:{porta} (Ctrl+C encerra)")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrado.")


if __name__ == "__main__":
    main()
