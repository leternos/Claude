#!/usr/bin/env python3
"""Webapp de consulta ao DJEN por OAB/SP.

Uso:  python3 app.py [porta]   (padrão: 8859)
Abra http://localhost:8859 no navegador.
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
<title>DJEN — Publicações OAB/SP</title>
<style>
  :root { --tinta: #1e232b; --papel: #f6f4ef; --cartao: #fff; --borda: #ddd6c8;
          --realce: #8a5a2b; --suave: #5a6472; }
  * { box-sizing: border-box; }
  body { font-family: Georgia, 'Times New Roman', serif; margin: 0;
         background: var(--papel); color: var(--tinta); }
  header.topo { padding: 1.5rem 2rem 1rem; border-bottom: 1px solid var(--borda); }
  h1 { margin: 0; font-size: 1.5rem; }
  .sub { color: var(--suave); margin: .25rem 0 0; font-size: .95rem; }
  main { max-width: 60rem; margin: 0 auto; padding: 1.5rem 1rem 4rem; }
  form { background: var(--cartao); border: 1px solid var(--borda); border-radius: 10px;
         padding: 1rem 1.25rem; display: grid; gap: .9rem;
         grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr)); }
  label { display: flex; flex-direction: column; gap: .3rem; font-size: .85rem;
          color: var(--suave); }
  input, select { font: inherit; padding: .45rem .6rem; border: 1px solid var(--borda);
                  border-radius: 6px; background: #fffdf8; color: var(--tinta); }
  .acoes { grid-column: 1 / -1; display: flex; flex-wrap: wrap; gap: .6rem; }
  button { font: inherit; padding: .5rem 1.1rem; border-radius: 6px; cursor: pointer;
           border: 1px solid var(--realce); background: var(--realce); color: #fff; }
  button.secundario { background: transparent; color: var(--realce); }
  button:disabled { opacity: .5; cursor: wait; }
  #status { margin: 1rem 0; color: var(--suave); }
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
</style>
</head>
<body>
<header class="topo">
  <h1>DJEN — Diário de Justiça Eletrônico Nacional</h1>
  <p class="sub">Consulta de publicações por OAB e exportação do dia · fonte:
     comunicaapi.pje.jus.br (CNJ)</p>
</header>
<main>
  <form id="form">
    <label>Número da OAB
      <input name="numeroOab" id="numeroOab" inputmode="numeric" placeholder="ex.: 123456" required>
    </label>
    <label>UF da OAB
      <select name="ufOab" id="ufOab"></select>
    </label>
    <label>Data inicial
      <input type="date" name="dataInicio" id="dataInicio" required>
    </label>
    <label>Data final
      <input type="date" name="dataFim" id="dataFim" required>
    </label>
    <label>Tribunal (opcional)
      <input name="siglaTribunal" id="siglaTribunal" placeholder="ex.: TJSP">
    </label>
    <div class="acoes">
      <button type="submit" id="btnBuscar">Buscar</button>
      <button type="button" class="secundario" data-fmt="csv">Exportar CSV</button>
      <button type="button" class="secundario" data-fmt="html">Exportar HTML</button>
      <button type="button" class="secundario" data-fmt="json">Exportar JSON</button>
      <button type="button" class="secundario" id="btnSalvar"
              title="Salva OAB/UF/tribunal como padrão para a exportação diária">
        Salvar como padrão</button>
    </div>
  </form>
  <p id="status">Informe o número da OAB e clique em Buscar.</p>
  <section id="resultados"></section>
</main>
<script>
const UFS = ["AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT","PA",
  "PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"];
const selUF = document.getElementById("ufOab");
UFS.forEach(uf => selUF.add(new Option(uf, uf, uf === "SP", uf === "SP")));

const hoje = new Date().toLocaleDateString("sv", {timeZone: "America/Sao_Paulo"});
dataInicio.value = hoje; dataFim.value = hoje;

fetch("/api/config").then(r => r.json()).then(cfg => {
  if (cfg.numeroOab) numeroOab.value = cfg.numeroOab;
  if (cfg.ufOab) selUF.value = cfg.ufOab;
  if (cfg.siglaTribunal) siglaTribunal.value = cfg.siglaTribunal;
});

function parametros() {
  return new URLSearchParams({
    numeroOab: numeroOab.value.trim(),
    ufOab: selUF.value,
    dataInicio: dataInicio.value,
    dataFim: dataFim.value,
    siglaTribunal: siglaTribunal.value.trim(),
  });
}

const status = document.getElementById("status");
const resultados = document.getElementById("resultados");
const esc = s => (s || "").replace(/[&<>"]/g,
  c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

document.getElementById("form").addEventListener("submit", async ev => {
  ev.preventDefault();
  const btn = document.getElementById("btnBuscar");
  btn.disabled = true;
  status.className = "";
  status.textContent = "Consultando o DJEN…";
  resultados.innerHTML = "";
  try {
    const r = await fetch("/api/search?" + parametros());
    const dados = await r.json();
    if (!r.ok) throw new Error(dados.erro || "Falha na consulta");
    status.textContent = dados.itens.length + " publicação(ões) encontrada(s).";
    resultados.innerHTML = dados.itens.map((p, i) => `
      <article class="pub">
        <span class="num">#${i + 1}</span>
        <strong>${esc(p.processo) || "(processo não informado)"}</strong>
        <span class="selo">${esc(p.tribunal)}</span>
        <span class="selo">${esc(p.tipo)}</span>
        ${p.link ? `<a href="${esc(p.link)}" target="_blank" rel="noopener">ver no DJEN</a>` : ""}
        <div class="meta">${esc(p.data)} · ${esc(p.orgao)} · ${esc(p.classe)}</div>
        <div class="meta">Partes: ${esc(p.partes) || "—"}</div>
        <div class="meta">Advogados(as): ${esc(p.advogados) || "—"}</div>
        <details><summary>Ver inteiro teor</summary>
          <div class="texto">${esc(p.texto).replace(/\\n/g, "<br>")}</div>
        </details>
      </article>`).join("");
  } catch (e) {
    status.className = "erro";
    status.textContent = "Erro: " + e.message;
  } finally {
    btn.disabled = false;
  }
});

document.querySelectorAll("button[data-fmt]").forEach(btn =>
  btn.addEventListener("click", () => {
    if (!numeroOab.value.trim()) { numeroOab.reportValidity(); return; }
    location.href = "/api/export?" + parametros() + "&formato=" + btn.dataset.fmt;
  }));

document.getElementById("btnSalvar").addEventListener("click", async () => {
  const r = await fetch("/api/config", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      numeroOab: numeroOab.value.trim(),
      ufOab: selUF.value,
      siglaTribunal: siglaTribunal.value.trim(),
    }),
  });
  status.className = r.ok ? "" : "erro";
  status.textContent = r.ok
    ? "Configuração salva — a exportação diária das 5:59 usará estes valores."
    : "Não foi possível salvar a configuração.";
});
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

    def _responder(self, corpo: bytes, tipo: str, status: int = 200,
                   download: str = ""):
        self.send_response(status)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        if download:
            self.send_header("Content-Disposition",
                             f'attachment; filename="{download}"')
        self.end_headers()
        self.wfile.write(corpo)

    def _json(self, dados, status: int = 200):
        self._responder(json.dumps(dados, ensure_ascii=False).encode("utf-8"),
                        "application/json; charset=utf-8", status)

    def _buscar(self, q: dict):
        return djen.buscar_comunicacoes(
            numero_oab=q.get("numeroOab", [""])[0],
            uf_oab=q.get("ufOab", ["SP"])[0],
            data_inicio=q.get("dataInicio", [""])[0] or None,
            data_fim=q.get("dataFim", [""])[0] or None,
            sigla_tribunal=q.get("siglaTribunal", [""])[0],
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
                            ("numeroOab", "ufOab", "siglaTribunal")})
            elif url.path == "/api/search":
                itens, total = self._buscar(q)
                self._json({"total": total, "itens": itens})
            elif url.path == "/api/export":
                itens, _ = self._buscar(q)
                fmt = q.get("formato", ["csv"])[0]
                oab = q.get("numeroOab", [""])[0]
                uf = q.get("ufOab", ["SP"])[0]
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
                                    "text/csv; charset=utf-8",
                                    download=f"{nome}.csv")
            else:
                self._json({"erro": "Rota não encontrada"}, 404)
        except djen.DJENError as e:
            self._json({"erro": str(e)}, 502)
        except Exception as e:  # noqa: BLE001 — servidor local, erro vai para a UI
            self._json({"erro": f"Erro interno: {e}"}, 500)

    def do_POST(self):
        if urllib.parse.urlparse(self.path).path != "/api/config":
            self._json({"erro": "Rota não encontrada"}, 404)
            return
        try:
            tamanho = int(self.headers.get("Content-Length", 0))
            novos = json.loads(self.rfile.read(tamanho).decode("utf-8"))
            cfg = carregar_config()
            for chave in ("numeroOab", "ufOab", "siglaTribunal"):
                if chave in novos:
                    cfg[chave] = str(novos[chave]).strip()
            with open(CONFIG, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
                f.write("\n")
            self._json({"ok": True})
        except Exception as e:  # noqa: BLE001
            self._json({"erro": f"Erro ao salvar: {e}"}, 500)

    def log_message(self, formato, *args):
        sys.stderr.write(f"[djen-oab-sp] {self.address_string()} {formato % args}\n")


def main():
    porta = int(sys.argv[1]) if len(sys.argv) > 1 else PORTA_PADRAO
    servidor = ThreadingHTTPServer(("127.0.0.1", porta), Handler)
    print(f"DJEN OAB/SP no ar: http://localhost:{porta} (Ctrl+C para encerrar)")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrado.")


if __name__ == "__main__":
    main()
