"""Cliente da API pública do DJEN (Diário de Justiça Eletrônico Nacional).

API oficial do CNJ: https://comunicaapi.pje.jus.br/api/v1/comunicacao
Atenção: o CDN do CNJ bloqueia IPs de fora do Brasil (HTTP 403).
"""

import csv
import html as html_mod
import io
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime
from zoneinfo import ZoneInfo

API_BASE = os.environ.get("DJEN_API_BASE", "https://comunicaapi.pje.jus.br")
ENDPOINT = "/api/v1/comunicacao"
USER_AGENT = "djen-oab-sp/1.0 (monitor de publicacoes; uso pessoal)"
FUSO_BRASILIA = ZoneInfo("America/Sao_Paulo")

# A API do CNJ bloqueia IPs fora do Brasil (HTTP 403). Para rodar de outro país
# (ex.: buscar inline no chat), aponte DJEN_PROXY para um proxy/VPS no Brasil:
#   export DJEN_PROXY="http://usuario:senha@meu-proxy-br:8080"
DJEN_PROXY = os.environ.get("DJEN_PROXY", "").strip()

if DJEN_PROXY:
    _OPENER = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": DJEN_PROXY, "https": DJEN_PROXY}))
else:
    _OPENER = urllib.request.build_opener()

ITENS_POR_PAGINA = 100
MAX_PAGINAS = 50
TENTATIVAS = 3


class DJENError(Exception):
    pass


class GeoBloqueioError(DJENError):
    def __init__(self):
        super().__init__(
            "A API do DJEN retornou HTTP 403: o CDN do CNJ bloqueia acessos de fora "
            "do Brasil. Execute este programa em uma máquina/rede com IP brasileiro."
        )


def hoje_brasilia() -> date:
    return datetime.now(FUSO_BRASILIA).date()


def _requisitar(url: str) -> dict:
    ultimo_erro = None
    for tentativa in range(TENTATIVAS):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
            })
            with _OPENER.open(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 403:
                raise GeoBloqueioError() from e
            ultimo_erro = DJENError(f"HTTP {e.code} na API do DJEN: {e.reason}")
            if e.code < 500:
                raise ultimo_erro from e
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            ultimo_erro = DJENError(f"Falha ao consultar a API do DJEN: {e}")
        time.sleep(2 * (tentativa + 1))
    raise ultimo_erro


def buscar_comunicacoes(numero_oab="", uf_oab="SP", data_inicio=None, data_fim=None,
                        sigla_tribunal="", nome_advogado="", nome_parte="",
                        numero_processo=""):
    """Busca todas as páginas de comunicações e retorna (itens_normalizados, total)."""
    if not any([numero_oab, nome_advogado, nome_parte, numero_processo]):
        raise DJENError("Informe ao menos o número da OAB (ou nome/processo) para a busca.")

    data_inicio = data_inicio or hoje_brasilia().isoformat()
    data_fim = data_fim or data_inicio

    params = {
        "dataDisponibilizacaoInicio": data_inicio,
        "dataDisponibilizacaoFim": data_fim,
        "itensPorPagina": ITENS_POR_PAGINA,
    }
    if numero_oab:
        params["numeroOab"] = re.sub(r"\D", "", str(numero_oab))
        params["ufOab"] = (uf_oab or "SP").upper()
    if sigla_tribunal:
        params["siglaTribunal"] = sigla_tribunal.upper()
    if nome_advogado:
        params["nomeAdvogado"] = nome_advogado
    if nome_parte:
        params["nomeParte"] = nome_parte
    if numero_processo:
        params["numeroProcesso"] = re.sub(r"\D", "", numero_processo)

    itens, vistos, total = [], set(), 0
    for pagina in range(1, MAX_PAGINAS + 1):
        params["pagina"] = pagina
        url = f"{API_BASE}{ENDPOINT}?{urllib.parse.urlencode(params)}"
        dados = _requisitar(url)
        total = dados.get("count") or dados.get("total") or 0
        lote = dados.get("items") or []
        for bruto in lote:
            item = normalizar_item(bruto)
            chave = item["id"] or item["hash"] or json.dumps(bruto, sort_keys=True)[:200]
            if chave not in vistos:
                vistos.add(chave)
                itens.append(item)
        if len(lote) < ITENS_POR_PAGINA or (total and len(itens) >= total):
            break
        time.sleep(0.3)
    return itens, (total or len(itens))


def normalizar_item(bruto: dict) -> dict:
    advogados = []
    for da in bruto.get("destinatarioadvogados") or []:
        adv = (da or {}).get("advogado") or {}
        nome = adv.get("nome", "")
        oab = adv.get("numero_oab", "")
        uf = adv.get("uf_oab", "")
        if nome or oab:
            advogados.append(f"{nome} (OAB {oab}/{uf})" if oab else nome)
    partes = [d.get("nome", "") for d in (bruto.get("destinatarios") or []) if d.get("nome")]
    texto_html = bruto.get("texto") or ""
    return {
        "id": bruto.get("id"),
        "hash": bruto.get("hash", ""),
        "data": bruto.get("data_disponibilizacao") or bruto.get("datadisponibilizacao") or "",
        "tribunal": bruto.get("siglaTribunal") or bruto.get("sigla_tribunal") or "",
        "tipo": bruto.get("tipoComunicacao") or bruto.get("tipo_comunicacao") or "",
        "documento": bruto.get("tipoDocumento") or "",
        "orgao": bruto.get("nomeOrgao") or bruto.get("nome_orgao") or "",
        "processo": bruto.get("numeroprocessocommascara") or bruto.get("numero_processo") or "",
        "classe": bruto.get("nomeClasse") or "",
        "partes": "; ".join(partes),
        "advogados": "; ".join(advogados),
        "link": bruto.get("link") or "",
        "texto_html": texto_html,
        "texto": limpar_html(texto_html),
    }


def limpar_html(texto: str) -> str:
    texto = re.sub(r"<\s*(br|/p|/div|/tr)[^>]*>", "\n", texto, flags=re.I)
    texto = re.sub(r"<[^>]+>", " ", texto)
    texto = html_mod.unescape(texto)
    texto = re.sub(r"[ \t]+", " ", texto)
    return re.sub(r"\n\s*\n+", "\n\n", texto).strip()


COLUNAS_CSV = ["data", "tribunal", "tipo", "documento", "orgao", "processo",
               "classe", "partes", "advogados", "link", "texto"]


def gerar_csv(itens: list) -> str:
    buf = io.StringIO()
    escritor = csv.DictWriter(buf, fieldnames=COLUNAS_CSV, extrasaction="ignore",
                              delimiter=";", quoting=csv.QUOTE_ALL)
    escritor.writeheader()
    for item in itens:
        escritor.writerow(item)
    return "﻿" + buf.getvalue()  # BOM para o Excel abrir com acentuação correta


def gerar_json(itens: list) -> str:
    return json.dumps(itens, ensure_ascii=False, indent=2)


def gerar_html(itens: list, titulo: str, subtitulo: str = "") -> str:
    esc = html_mod.escape
    cartoes = []
    for i, item in enumerate(itens, 1):
        meta = " · ".join(filter(None, [
            esc(item["data"]), esc(item["tribunal"]), esc(item["tipo"]),
            esc(item["orgao"]), esc(item["classe"]),
        ]))
        link = (f'<a href="{esc(item["link"])}" target="_blank" rel="noopener">'
                f'ver no DJEN</a>' if item["link"] else "")
        cartoes.append(f"""
  <article class="pub">
    <header>
      <span class="num">#{i}</span>
      <strong>{esc(item["processo"]) or "(processo não informado)"}</strong> {link}
      <div class="meta">{meta}</div>
      <div class="meta">Partes: {esc(item["partes"]) or "—"}</div>
      <div class="meta">Advogados(as): {esc(item["advogados"]) or "—"}</div>
    </header>
    <div class="texto">{item["texto_html"] or esc(item["texto"])}</div>
  </article>""")
    corpo = "\n".join(cartoes) or '<p class="vazio">Nenhuma publicação encontrada.</p>'
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(titulo)}</title>
<style>
  body {{ font-family: Georgia, 'Times New Roman', serif; margin: 0; padding: 2rem;
         background: #f6f4ef; color: #1e232b; }}
  h1 {{ font-size: 1.4rem; margin: 0 0 .25rem; }}
  .sub {{ color: #5a6472; margin: 0 0 1.5rem; }}
  .pub {{ background: #fff; border: 1px solid #ddd6c8; border-radius: 8px;
          padding: 1rem 1.25rem; margin-bottom: 1rem; page-break-inside: avoid; }}
  .pub header {{ margin-bottom: .5rem; }}
  .num {{ color: #8a5a2b; font-weight: bold; margin-right: .5rem; }}
  .meta {{ color: #5a6472; font-size: .85rem; }}
  .texto {{ font-size: .95rem; line-height: 1.55; border-top: 1px dashed #ddd6c8;
            padding-top: .5rem; overflow-wrap: anywhere; }}
  .vazio {{ color: #5a6472; font-style: italic; }}
  a {{ color: #8a5a2b; }}
  @media print {{ body {{ background: #fff; padding: 0; }} }}
</style>
</head>
<body>
<h1>{esc(titulo)}</h1>
<p class="sub">{esc(subtitulo)}</p>
{corpo}
</body>
</html>
"""


def resumo_texto(itens: list, numero_oab: str, uf_oab: str, data_inicio: str,
                 data_fim: str) -> str:
    periodo = data_inicio if data_inicio == data_fim else f"{data_inicio} a {data_fim}"
    linhas = [
        f"DJEN — publicações para OAB {numero_oab}/{uf_oab} em {periodo}",
        f"Total: {len(itens)} publicação(ões)",
        "",
    ]
    if not itens:
        linhas.append("Nenhuma publicação encontrada nesta data.")
    for i, item in enumerate(itens, 1):
        linhas.append(f"{i}. [{item['tribunal']}] {item['tipo']} — processo "
                      f"{item['processo'] or '(sem número)'}")
        if item["orgao"]:
            linhas.append(f"   Órgão: {item['orgao']}")
        if item["partes"]:
            linhas.append(f"   Partes: {item['partes']}")
        trecho = item["texto"][:300].replace("\n", " ")
        if trecho:
            linhas.append(f"   Trecho: {trecho}{'…' if len(item['texto']) > 300 else ''}")
        linhas.append("")
    return "\n".join(linhas)
