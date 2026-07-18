#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tonico.py — Estudo do estilo de escrita de Antonio Carlos Monteiro da Silva Filho (OAB/SP 124.536)

Pipeline completo, sem dependências obrigatórias fora da biblioteca-padrão:

  python3 tonico.py buscar              imprime links de busca prontos (Google, JusBrasil,
                                        Escavador, e-SAJ) para localizar peças e publicações
  python3 tonico.py ingerir [ALVOS...]  lê PDF/DOCX/HTML/TXT de ./corpus (padrão), de
                                        caminhos ou de URLs e grava no banco SQLite
  python3 tonico.py analisar            calcula métricas de estilo, ranking de palavras,
                                        heurísticas, citações e tendências
  python3 tonico.py relatorio           gera ./relatorios/relatorio.md
  python3 tonico.py tudo                ingerir + analisar + relatorio

PDF: usa pypdf/PyPDF2 se instalado; senão tenta o binário `pdftotext`; senão pula com aviso.
URLs listadas em ./corpus/fontes.txt (uma por linha) também são baixadas no `ingerir`.
"""

import argparse
import datetime
import hashlib
import html
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unicodedata
import urllib.parse
import urllib.request
import zipfile
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

BASE = Path(__file__).resolve().parent
CORPUS = BASE / "corpus"
BAIXADOS = CORPUS / "baixados"
BANCO = BASE / "banco" / "estilo.db"
RELATORIOS = BASE / "relatorios"

CLIENTE = "Antonio Carlos Monteiro da Silva Filho"
OAB = "OAB/SP 124.536"
OAB_NUMERO = "124536"

# ---------------------------------------------------------------------------
# Léxicos
# ---------------------------------------------------------------------------

STOPWORDS = set("""
a à às ao aos as o os um uma uns umas de do da dos das dum duma em no na nos nas
num numa por pelo pela pelos pelas com sem sob sobre para pra entre contra desde
até após ante perante e ou mas nem que se como quando onde porque pois porém
todavia contudo entretanto logo portanto assim então já ainda também só somente
apenas mesmo mesma mesmos mesmas muito muita muitos muitas pouco pouca poucos
poucas mais menos tão tanto tanta tantos tantas qual quais quem cujo cuja cujos
cujas este esta estes estas isto esse essa esses essas isso aquele aquela aqueles
aquelas aquilo seu sua seus suas meu minha meus minhas teu tua nosso nossa nossos
nossas dele dela deles delas eu tu ele ela nós vós eles elas me te lhe lhes vos
si consigo ser é são foi foram era eram será serão seria seriam sendo sido estar
está estão estava estavam esteve estiveram estará estando estado ter tem têm
tinha tinham teve tiveram terá terão teria tendo tido haver há havia houve haja
hão vai vão não sim ora seja sejam fosse fossem for forem deve devem pode podem
podendo qualquer quaisquer cada outro outra outros outras todo toda todos todas
algum alguma alguns algumas nenhum nenhuma tal tais lá cá aqui ali aí bem mal
""".split())

# Nos léxicos abaixo, "*" no fim marca radical (casa qualquer sufixo);
# sem "*", a expressão só casa como palavra/locução inteira.
LATINISMOS = [
    "data venia", "concessa venia", "permissa venia", "in casu", "ab initio",
    "ex vi", "in verbis", "ipsis litteris", "ipsis verbis", "a quo", "ad quem",
    "ex positis", "in fine", "mutatis mutandis", "pari passu", "ex officio",
    "de cujus", "erga omnes", "ex tunc", "ex nunc", "in dubio pro reo",
    "fumus boni iuris", "periculum in mora", "ultra petita", "extra petita",
    "citra petita", "ad cautelam", "in limine", "prima facie", "sub judice",
    "apud", "ad argumentandum",
]

CORTESIA = [
    "douto", "doutos", "ilustre", "nobre", "colend*", "egrégi*", "eminente",
    "respeitável", "vossa excelência", "culto julgador", "insigne", "preclaro",
]

COMBATIVIDADE = [
    "absurd*", "teratológic*", "inadmissível", "escancarad*", "flagrante",
    "litigância de má-fé", "má-fé", "descabid*", "esdrúxul*", "despropositad*",
    "temerári*", "afronta*", "inaceitável", "gritante",
]

ASSERTIVIDADE = [
    "resta claro", "resta evidente", "é evidente", "inequívoc*", "indubitável",
    "inquestionável", "certamente", "sem dúvida", "impõe-se", "forçoso concluir",
    "não há como negar", "cristalino", "é cediço", "como se sabe",
]

CAUTELA = [
    "salvo melhor juízo", "s.m.j", "ao que parece", "possivelmente", "talvez",
    "em tese", "aparentemente", "supostamente", "eventualmente",
    "caso se entenda", "ad argumentandum tantum", "por cautela",
]

CONECTIVOS = [
    "portanto", "destarte", "outrossim", "ademais", "dessarte", "nesse sentido",
    "nesse diapasão", "com efeito", "de outro giro", "por conseguinte",
    "assim sendo", "isto posto", "isso posto", "ante o exposto",
    "diante do exposto", "nada obstante", "não obstante", "máxime", "por óbvio",
    "frise-se", "registre-se", "insta salientar", "cumpre destacar",
    "cumpre salientar", "vale dizer", "é dizer", "noutro norte",
]

PRINCIPIOS = [
    "dignidade da pessoa humana", "devido processo legal", "contraditório",
    "ampla defesa", "proporcionalidade", "razoabilidade", "boa-fé objetiva",
    "boa-fé", "segurança jurídica", "legalidade", "isonomia", "impessoalidade",
    "moralidade", "eficiência", "função social", "duração razoável do processo",
    "acesso à justiça", "presunção de inocência", "pacta sunt servanda",
    "supremacia do interesse público", "livre convencimento",
    "primazia da realidade", "vedação ao enriquecimento sem causa",
]

AUTORES = [
    "kelsen", "alexy", "dworkin", "hart", "bobbio", "ferrajoli", "radbruch",
    "habermas", "rawls", "foucault", "aristóteles", "kant", "hegel",
    "montesquieu", "beccaria", "miguel reale", "pontes de miranda",
    "nelson nery", "barroso", "gilmar mendes", "dinamarco", "humberto theodoro",
    "didier", "tartuce", "cavalieri", "maria helena diniz",
    "bandeira de mello", "hely lopes", "josé afonso da silva", "canotilho",
    "ada pellegrini", "calamandrei", "carnelutti", "chiovenda", "liebman",
]

CORRENTES = [
    "positivis*", "jusnaturalis*", "direito natural", "garantis*",
    "neoconstitucional*", "pós-positivis*", "utilitaris*", "pragmatis*",
    "consequencialis*", "ativismo judicial", "hermenêutic*", "ponderação",
    "tridimensional",
]

CATEGORIAS_EXPRESSOES = {
    "latinismo": LATINISMOS,
    "cortesia": CORTESIA,
    "combatividade": COMBATIVIDADE,
    "assertividade": ASSERTIVIDADE,
    "cautela": CAUTELA,
    "conectivo": CONECTIVOS,
    "principio": PRINCIPIOS,
    "autor": AUTORES,
    "corrente": CORRENTES,
}

PADROES_CITACAO = {
    "legislacao": [
        r"\blei\s+(?:complementar\s+)?(?:n[ºo°.]*\s*)?[\d.]+(?:/\d{2,4})?",
        r"\bdecreto(?:-lei)?\s+(?:n[ºo°.]*\s*)?[\d.]+(?:/\d{2,4})?",
        r"\bmedida\s+provis[óo]ria\s+(?:n[ºo°.]*\s*)?[\d.]+",
        r"\bconstitui[çc][ãa]o\s+federal\b", r"\bcf/?88\b",
        r"\b(?:cpc|clt|ctn|cdc|cpp|eca)\b",
        r"\bc[óo]digo\s+(?:civil|penal|tribut[áa]rio|de\s+processo\s+\w+|de\s+defesa\s+do\s+consumidor)",
    ],
    "jurisprudencia": [
        r"\b(?:stf|stj|tst|tse|stm)\b",
        r"\btj[a-z]{2}\b", r"\btrf-?\d\b", r"\btrt-?\d+\b",
        r"\bs[úu]mula\s+(?:vinculante\s+)?(?:n[ºo°.]*\s*)?\d+",
        r"\b(?:resp|aresp|eresp|agrg|edcl|are|adi|adc|adpf|rhc)\s*(?:n[ºo°.]*\s*)?[\d.]+",
        r"\b(?:re|hc|ms)\s+(?:n[ºo°.]*\s*)?[\d.]{3,}",
        r"\brecurso\s+(?:especial|extraordin[áa]rio)",
        r"\btema\s+(?:repetitivo\s+)?(?:n[ºo°.]*\s*)?\d+",
    ],
}

PADRAO_ARTIGO = re.compile(r"\bart(?:igo)?s?\.?\s*\d+", re.IGNORECASE)
# SOBRENOME, Nome — citação doutrinária em formato ABNT (roda no texto original)
PADRAO_DOUTRINA_ABNT = re.compile(
    r"\b([A-ZÁÉÍÓÚÂÊÔÃÕÇ]{3,}(?:\s+(?:DE|DA|DO|DOS|DAS|E)?\s*[A-ZÁÉÍÓÚÂÊÔÃÕÇ]{2,}){0,3}),\s+[A-Z][a-záéíóúâêôãõç]+"
)

MESES = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "abril": 4, "maio": 5,
    "junho": 6, "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10,
    "novembro": 11, "dezembro": 12,
}
PADRAO_DATA = re.compile(
    r"\b(\d{1,2})\s+de\s+(" + "|".join(MESES) + r")\s+de\s+((?:19|20)\d{2})",
    re.IGNORECASE,
)

TOKEN = re.compile(r"[a-záàâãéêíóôõúüç]+")
LETRA = "a-záàâãéêíóôõúüç"

# assinatura do cliente não deve poluir o ranking de vocabulário
EXCLUIR_RANKING = set(CLIENTE.lower().split()) | {"oab"}


def _contar(minusculo: str, expressao: str) -> int:
    """Conta ocorrências com fronteira de palavra; sufixo '*' marca radical."""
    radical = expressao.endswith("*")
    padrao = rf"(?<![{LETRA}-])" + re.escape(expressao.rstrip("*"))
    if not radical:
        padrao += rf"(?![{LETRA}-])"
    return len(re.findall(padrao, minusculo))

# ---------------------------------------------------------------------------
# Extração de texto
# ---------------------------------------------------------------------------


class _ExtratorHTML(HTMLParser):
    IGNORAR = {"script", "style", "nav", "header", "footer", "noscript"}

    def __init__(self):
        super().__init__()
        self.trechos = []
        self._pilha_ignorar = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.IGNORAR:
            self._pilha_ignorar += 1

    def handle_endtag(self, tag):
        if tag in self.IGNORAR and self._pilha_ignorar:
            self._pilha_ignorar -= 1

    def handle_data(self, data):
        if not self._pilha_ignorar and data.strip():
            self.trechos.append(data.strip())


def _extrair_html(conteudo: str) -> str:
    parser = _ExtratorHTML()
    parser.feed(conteudo)
    return "\n".join(parser.trechos)


def _extrair_docx(caminho: Path) -> str:
    with zipfile.ZipFile(caminho) as z:
        xml = z.read("word/document.xml").decode("utf-8", errors="ignore")
    xml = xml.replace("</w:p>", "\n").replace("<w:tab/>", "\t")
    return html.unescape(re.sub(r"<[^>]+>", "", xml))


def _extrair_pdf(caminho: Path) -> str:
    leitor = None
    try:
        from pypdf import PdfReader as leitor
    except ImportError:
        try:
            from PyPDF2 import PdfReader as leitor
        except ImportError:
            pass
    if leitor is not None:
        paginas = leitor(str(caminho)).pages
        return "\n".join((p.extract_text() or "") for p in paginas)
    if shutil.which("pdftotext"):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            destino = tmp.name
        subprocess.run(["pdftotext", "-layout", str(caminho), destino], check=True)
        texto = Path(destino).read_text(encoding="utf-8", errors="ignore")
        Path(destino).unlink(missing_ok=True)
        return texto
    print(f"  [aviso] sem pypdf nem pdftotext — pulei {caminho.name}"
          "  (instale com: pip install pypdf)")
    return ""


def extrair_texto(caminho: Path) -> str:
    ext = caminho.suffix.lower()
    if ext == ".pdf":
        return _extrair_pdf(caminho)
    if ext == ".docx":
        return _extrair_docx(caminho)
    bruto = caminho.read_text(encoding="utf-8", errors="ignore")
    if ext in (".html", ".htm") or bruto.lstrip()[:1] == "<":
        return _extrair_html(bruto)
    return bruto


def baixar_url(url: str) -> Path | None:
    BAIXADOS.mkdir(parents=True, exist_ok=True)
    nome = re.sub(r"[^\w.-]+", "_", urllib.parse.urlparse(url).path) or "pagina"
    if "." not in nome.rsplit("/", 1)[-1]:
        nome += ".html"
    destino = BAIXADOS / nome.strip("_")
    try:
        pedido = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(pedido, timeout=60) as resposta:
            destino.write_bytes(resposta.read())
        print(f"  baixado: {url} -> {destino.name}")
        return destino
    except Exception as erro:
        print(f"  [erro] não consegui baixar {url}: {erro}")
        return None


# ---------------------------------------------------------------------------
# Banco de dados
# ---------------------------------------------------------------------------

ESQUEMA = """
CREATE TABLE IF NOT EXISTS documentos (
    id          INTEGER PRIMARY KEY,
    hash        TEXT UNIQUE,
    titulo      TEXT,
    origem      TEXT,
    formato     TEXT,
    data_texto  TEXT,
    ano         INTEGER,
    n_palavras  INTEGER,
    texto       TEXT
);
CREATE TABLE IF NOT EXISTS palavras (
    doc_id INTEGER REFERENCES documentos(id),
    palavra TEXT, freq INTEGER
);
CREATE TABLE IF NOT EXISTS ngramas (
    doc_id INTEGER REFERENCES documentos(id),
    n INTEGER, ngrama TEXT, freq INTEGER
);
CREATE TABLE IF NOT EXISTS citacoes (
    doc_id INTEGER REFERENCES documentos(id),
    categoria TEXT, referencia TEXT
);
CREATE TABLE IF NOT EXISTS expressoes (
    doc_id INTEGER REFERENCES documentos(id),
    categoria TEXT, expressao TEXT, freq INTEGER
);
CREATE TABLE IF NOT EXISTS metricas (
    doc_id INTEGER REFERENCES documentos(id),
    nome TEXT, valor REAL
);
CREATE INDEX IF NOT EXISTS idx_palavras ON palavras(palavra);
"""


def abrir_banco() -> sqlite3.Connection:
    BANCO.parent.mkdir(parents=True, exist_ok=True)
    conexao = sqlite3.connect(BANCO)
    conexao.executescript(ESQUEMA)
    return conexao


# ---------------------------------------------------------------------------
# Comando: ingerir
# ---------------------------------------------------------------------------


def _detectar_data(texto: str, nome: str):
    datas = PADRAO_DATA.findall(texto)
    if datas:
        dia, mes, ano = datas[-1]  # a assinatura costuma ficar no fim da peça
        return f"{int(dia):02d}/{MESES[mes.lower()]:02d}/{ano}", int(ano)
    ano_nome = re.search(r"\b(19|20)\d{2}\b", nome)
    if ano_nome:
        return None, int(ano_nome.group())
    return None, None


def ingerir(alvos):
    conexao = abrir_banco()
    arquivos = []
    if not alvos:
        CORPUS.mkdir(parents=True, exist_ok=True)
        alvos = [str(CORPUS)]
        fontes = CORPUS / "fontes.txt"
        if fontes.exists():
            alvos += [l.strip() for l in fontes.read_text().splitlines()
                      if l.strip() and not l.startswith("#")]
    for alvo in alvos:
        if alvo.startswith(("http://", "https://")):
            baixado = baixar_url(alvo)
            if baixado:
                arquivos.append(baixado)
            continue
        caminho = Path(alvo)
        if caminho.is_dir():
            arquivos += sorted(p for p in caminho.rglob("*")
                               if p.suffix.lower() in (".pdf", ".docx", ".txt", ".html", ".htm")
                               and p.name != "fontes.txt")
        elif caminho.is_file():
            arquivos.append(caminho)
        else:
            print(f"  [aviso] alvo não encontrado: {alvo}")

    novos = 0
    for arquivo in arquivos:
        texto = extrair_texto(arquivo).strip()
        if len(texto) < 200:
            print(f"  [aviso] texto curto/vazio, pulei: {arquivo.name}")
            continue
        digestor = hashlib.sha1(texto.encode("utf-8")).hexdigest()
        data_texto, ano = _detectar_data(texto, arquivo.name)
        try:
            conexao.execute(
                "INSERT INTO documentos (hash, titulo, origem, formato, data_texto, ano, n_palavras, texto)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (digestor, arquivo.stem, str(arquivo), arquivo.suffix.lstrip("."),
                 data_texto, ano, len(TOKEN.findall(texto.lower())), texto))
            novos += 1
            print(f"  ingerido: {arquivo.name}" + (f" ({data_texto})" if data_texto else ""))
        except sqlite3.IntegrityError:
            print(f"  já estava no banco: {arquivo.name}")
    conexao.commit()
    total = conexao.execute("SELECT COUNT(*) FROM documentos").fetchone()[0]
    print(f"\n{novos} documento(s) novo(s); {total} no banco ({BANCO.relative_to(BASE)}).")
    conexao.close()


# ---------------------------------------------------------------------------
# Comando: analisar
# ---------------------------------------------------------------------------


def _analisar_documento(conexao, doc_id, texto):
    minusculo = texto.lower()
    tokens = TOKEN.findall(minusculo)
    n_tokens = len(tokens)
    if not n_tokens:
        return

    conteudo = [t for t in tokens
                if t not in STOPWORDS and t not in EXCLUIR_RANKING and len(t) > 2]
    for palavra, freq in Counter(conteudo).items():
        conexao.execute("INSERT INTO palavras VALUES (?,?,?)", (doc_id, palavra, freq))

    for n in (2, 3):
        gramas = Counter(" ".join(tokens[i:i + n]) for i in range(n_tokens - n + 1))
        gramas = Counter({g: f for g, f in gramas.items()
                          if f > 1 and not all(p in STOPWORDS for p in g.split())})
        for grama, freq in gramas.most_common(200):
            conexao.execute("INSERT INTO ngramas VALUES (?,?,?,?)", (doc_id, n, grama, freq))

    total_citacoes = 0
    for categoria, padroes in PADROES_CITACAO.items():
        for padrao in padroes:
            for achado in re.findall(padrao, minusculo):
                ref = re.sub(r"\s+", " ", achado).strip(" .,")
                conexao.execute("INSERT INTO citacoes VALUES (?,?,?)", (doc_id, categoria, ref))
                total_citacoes += 1
    artigos = PADRAO_ARTIGO.findall(texto)
    total_citacoes += len(artigos)
    for sobrenome in {m.group(1).title() for m in PADRAO_DOUTRINA_ABNT.finditer(texto)}:
        conexao.execute("INSERT INTO citacoes VALUES (?,?,?)", (doc_id, "doutrina", sobrenome))
        total_citacoes += 1

    contagens = {}
    for categoria, expressoes in CATEGORIAS_EXPRESSOES.items():
        soma = 0
        for expressao in expressoes:
            freq = _contar(minusculo, expressao)
            if freq:
                conexao.execute("INSERT INTO expressoes VALUES (?,?,?,?)",
                                (doc_id, categoria, expressao.rstrip("*"), freq))
                soma += freq
        contagens[categoria] = soma

    frases = [f for f in re.split(r"[.!?]+\s", texto) if TOKEN.search(f.lower())]
    amostra = tokens[:1000]
    singular = sum(_contar(minusculo, v) for v in
                   ("entendo", "sustento", "requeiro", "venho", "postulo", "defendo que"))
    plural = sum(_contar(minusculo, v) for v in
                 ("entendemos", "sustentamos", "requeremos", "vimos", "postulamos"))
    por_mil = lambda x: 1000 * x / n_tokens
    metricas = {
        "palavras": n_tokens,
        "frases": len(frases) or 1,
        "palavras_por_frase": n_tokens / (len(frases) or 1),
        "tamanho_medio_palavra": sum(map(len, tokens)) / n_tokens,
        "riqueza_lexical_ttr1000": len(set(amostra)) / len(amostra),
        "pct_palavras_longas": 100 * sum(1 for t in tokens if len(t) >= 10) / n_tokens,
        "artigos_de_lei_por_1000": por_mil(len(artigos)),
        "citacoes_por_1000": por_mil(total_citacoes),
        "latinismos_por_1000": por_mil(contagens["latinismo"]),
        "assertividade_por_1000": por_mil(contagens["assertividade"]),
        "cautela_por_1000": por_mil(contagens["cautela"]),
        "combatividade_por_1000": por_mil(contagens["combatividade"]),
        "cortesia_por_1000": por_mil(contagens["cortesia"]),
        "primeira_pessoa_singular": singular,
        "primeira_pessoa_plural": plural,
    }
    for nome, valor in metricas.items():
        conexao.execute("INSERT INTO metricas VALUES (?,?,?)", (doc_id, nome, valor))


def analisar():
    conexao = abrir_banco()
    documentos = conexao.execute("SELECT id, titulo, texto FROM documentos").fetchall()
    if not documentos:
        sys.exit("Banco vazio — rode antes: python3 tonico.py ingerir")
    for tabela in ("palavras", "ngramas", "citacoes", "expressoes", "metricas"):
        conexao.execute(f"DELETE FROM {tabela}")
    for doc_id, titulo, texto in documentos:
        print(f"  analisando: {titulo}")
        _analisar_documento(conexao, doc_id, texto)
    conexao.commit()
    conexao.close()
    print(f"\n{len(documentos)} documento(s) analisado(s).")


# ---------------------------------------------------------------------------
# Comando: relatorio
# ---------------------------------------------------------------------------


def _tabela(linhas, cabecalho):
    saida = ["| " + " | ".join(cabecalho) + " |",
             "|" + "|".join("---" for _ in cabecalho) + "|"]
    for linha in linhas:
        saida.append("| " + " | ".join(str(c) for c in linha) + " |")
    return "\n".join(saida) if linhas else "_sem dados_"


def relatorio():
    conexao = abrir_banco()
    consultar = lambda sql, *p: conexao.execute(sql, p).fetchall()
    n_docs, n_palavras = consultar(
        "SELECT COUNT(*), COALESCE(SUM(n_palavras),0) FROM documentos")[0]
    if not n_docs:
        sys.exit("Banco vazio — rode antes: python3 tonico.py tudo")

    media = {nome: valor for nome, valor in consultar(
        "SELECT nome, AVG(valor) FROM metricas GROUP BY nome")}
    if not media:
        sys.exit("Sem análise — rode antes: python3 tonico.py analisar")

    topo_palavras = consultar(
        "SELECT palavra, SUM(freq) f FROM palavras GROUP BY palavra ORDER BY f DESC LIMIT 50")
    topo_bigramas = consultar(
        "SELECT ngrama, SUM(freq) f FROM ngramas WHERE n=2 GROUP BY ngrama ORDER BY f DESC LIMIT 20")
    topo_trigramas = consultar(
        "SELECT ngrama, SUM(freq) f FROM ngramas WHERE n=3 GROUP BY ngrama ORDER BY f DESC LIMIT 20")
    topo_por_categoria = {
        categoria: consultar(
            "SELECT expressao, SUM(freq) f FROM expressoes WHERE categoria=?"
            " GROUP BY expressao ORDER BY f DESC LIMIT 15", categoria)
        for categoria in CATEGORIAS_EXPRESSOES}
    topo_citacoes = {
        categoria: consultar(
            "SELECT referencia, COUNT(*) f FROM citacoes WHERE categoria=?"
            " GROUP BY referencia ORDER BY f DESC LIMIT 15", categoria)
        for categoria in ("legislacao", "jurisprudencia", "doutrina")}
    por_ano = consultar("""
        SELECT d.ano, COUNT(DISTINCT d.id), AVG(m1.valor), AVG(m2.valor)
        FROM documentos d
        JOIN metricas m1 ON m1.doc_id=d.id AND m1.nome='citacoes_por_1000'
        JOIN metricas m2 ON m2.doc_id=d.id AND m2.nome='palavras_por_frase'
        WHERE d.ano IS NOT NULL GROUP BY d.ano ORDER BY d.ano""")
    documentos = consultar(
        "SELECT titulo, formato, COALESCE(data_texto, ano, '—'), n_palavras"
        " FROM documentos ORDER BY ano, titulo")

    singular = media.get("primeira_pessoa_singular", 0)
    plural = media.get("primeira_pessoa_plural", 0)
    voz = ("plural (nós) — tom institucional/de escritório" if plural > singular
           else "singular (eu) — tom pessoal e direto" if singular > plural
           else "equilíbrio entre singular e plural")
    tom = ("mais assertivo que cauteloso"
           if media["assertividade_por_1000"] > media["cautela_por_1000"]
           else "mais cauteloso/modalizado que assertivo")

    agora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    fmt = lambda v: f"{v:.2f}"
    secoes = [
        f"# Estudo de estilo — {CLIENTE} ({OAB})",
        f"_Gerado em {agora} · {n_docs} documento(s) · {n_palavras:,} palavras no corpus_".replace(",", "."),
        "## 1. Corpus",
        _tabela(documentos, ["Documento", "Formato", "Data", "Palavras"]),
        "## 2. Ranking de palavras mais usadas (sem stopwords)",
        _tabela([(i + 1, p, f) for i, (p, f) in enumerate(topo_palavras)],
                ["#", "Palavra", "Ocorrências"]),
        "## 3. Expressões características (bigramas e trigramas)",
        "### Bigramas", _tabela(topo_bigramas, ["Expressão", "Ocorrências"]),
        "### Trigramas", _tabela(topo_trigramas, ["Expressão", "Ocorrências"]),
        "## 4. Métricas de estilo (médias por documento)",
        _tabela([
            ("Palavras por frase", fmt(media["palavras_por_frase"])),
            ("Tamanho médio de palavra (letras)", fmt(media["tamanho_medio_palavra"])),
            ("Riqueza lexical (TTR nas 1.000 primeiras palavras)", fmt(media["riqueza_lexical_ttr1000"])),
            ("% de palavras longas (10+ letras)", fmt(media["pct_palavras_longas"])),
            ("Citações por 1.000 palavras (embasamento)", fmt(media["citacoes_por_1000"])),
            ("Artigos de lei por 1.000 palavras", fmt(media["artigos_de_lei_por_1000"])),
            ("Latinismos por 1.000 palavras", fmt(media["latinismos_por_1000"])),
        ], ["Métrica", "Valor"]),
        "## 5. Análise heurística e comportamental",
        _tabela([
            ("Assertividade por 1.000 palavras", fmt(media["assertividade_por_1000"])),
            ("Cautela/modalização por 1.000 palavras", fmt(media["cautela_por_1000"])),
            ("Combatividade por 1.000 palavras", fmt(media["combatividade_por_1000"])),
            ("Cortesia forense por 1.000 palavras", fmt(media["cortesia_por_1000"])),
        ], ["Indicador", "Valor"]),
        f"- **Tom predominante:** {tom}.",
        f"- **Voz preferida:** {voz}.",
        "### Conectivos preferidos (assinatura argumentativa)",
        _tabela(topo_por_categoria["conectivo"], ["Conectivo", "Ocorrências"]),
        "### Marcadores por categoria",
    ]
    for categoria in ("assertividade", "cautela", "combatividade", "cortesia", "latinismo"):
        linhas = topo_por_categoria[categoria]
        if linhas:
            secoes += [f"**{categoria.capitalize()}**", _tabela(linhas, ["Expressão", "Ocorrências"])]
    secoes += [
        "## 6. Embasamento e citações",
        "### Legislação mais citada",
        _tabela(topo_citacoes["legislacao"], ["Referência", "Ocorrências"]),
        "### Jurisprudência (tribunais, recursos e súmulas)",
        _tabela(topo_citacoes["jurisprudencia"], ["Referência", "Ocorrências"]),
        "### Doutrina citada em formato ABNT (SOBRENOME, Nome)",
        _tabela(topo_citacoes["doutrina"], ["Autor", "Documentos que citam"]),
        "## 7. Filosofia e fundamentos",
        "### Princípios jurídicos invocados",
        _tabela(topo_por_categoria["principio"], ["Princípio", "Ocorrências"]),
        "### Autores e pensadores mencionados",
        _tabela(topo_por_categoria["autor"], ["Autor", "Ocorrências"]),
        "### Correntes e métodos",
        _tabela(topo_por_categoria["corrente"], ["Termo", "Ocorrências"]),
        "## 8. Tendências ao longo do tempo",
        _tabela([(ano, docs, fmt(cit), fmt(ppf)) for ano, docs, cit, ppf in por_ano],
                ["Ano", "Docs", "Citações/1.000", "Palavras/frase"])
        if por_ano else "_Sem datas detectadas nos documentos — inclua a data na peça "
                        "ou o ano no nome do arquivo para habilitar esta seção._",
        "---",
        "_Relatório gerado por tonico.py. Heurísticas por léxico e regex: revise "
        "criticamente antes de usar em juízo — falsos positivos são possíveis._",
    ]

    RELATORIOS.mkdir(parents=True, exist_ok=True)
    destino = RELATORIOS / "relatorio.md"
    destino.write_text("\n\n".join(secoes), encoding="utf-8")
    conexao.close()
    print(f"Relatório gravado em {destino}")


# ---------------------------------------------------------------------------
# Comando: buscar
# ---------------------------------------------------------------------------


def buscar():
    aspas = urllib.parse.quote_plus(f'"{CLIENTE}"')
    com_oab = urllib.parse.quote_plus(f'"{CLIENTE}" OAB {OAB_NUMERO}')
    print(f"Links de busca para {CLIENTE} ({OAB}) — abra no navegador, salve os\n"
          f"PDFs/páginas em tonico/corpus/ (ou cole as URLs em corpus/fontes.txt):\n")
    for rotulo, url in [
        ("Google (nome + OAB)", f"https://www.google.com/search?q={com_oab}"),
        ("Google — JusBrasil", f"https://www.google.com/search?q={aspas}+site:jusbrasil.com.br"),
        ("Google — Escavador", f"https://www.google.com/search?q={aspas}+site:escavador.com"),
        ("Google — artigos (Migalhas/Conjur)",
         f"https://www.google.com/search?q={aspas}+(site:migalhas.com.br+OR+site:conjur.com.br)"),
        ("Escavador — busca direta", f"https://www.escavador.com/busca?q={aspas}&qo=t"),
        ("e-SAJ TJSP — consulta por OAB (preencher 124536SP)",
         "https://esaj.tjsp.jus.br/cpopg/open.do"),
        ("CNJ — consulta processual unificada", "https://www.cnj.jus.br/pjecnj/ConsultaPublica/listView.seam"),
        ("Google Acadêmico", f"https://scholar.google.com/scholar?q={aspas}"),
    ]:
        print(f"  • {rotulo}:\n    {url}")
    print("\nDepois rode: python3 tonico.py tudo")


# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description=f"Estudo de estilo de escrita — {CLIENTE} ({OAB})")
    sub = parser.add_subparsers(dest="comando", required=True)
    ing = sub.add_parser("ingerir", help="ingere documentos de ./corpus, caminhos ou URLs")
    ing.add_argument("alvos", nargs="*", help="arquivos, pastas ou URLs (padrão: ./corpus)")
    sub.add_parser("analisar", help="analisa os documentos do banco")
    sub.add_parser("relatorio", help="gera relatorios/relatorio.md")
    tudo = sub.add_parser("tudo", help="ingerir + analisar + relatorio")
    tudo.add_argument("alvos", nargs="*")
    sub.add_parser("buscar", help="imprime links de busca para localizar publicações")
    argumentos = parser.parse_args()

    if argumentos.comando == "buscar":
        buscar()
    elif argumentos.comando == "ingerir":
        ingerir(argumentos.alvos)
    elif argumentos.comando == "analisar":
        analisar()
    elif argumentos.comando == "relatorio":
        relatorio()
    elif argumentos.comando == "tudo":
        ingerir(argumentos.alvos)
        analisar()
        relatorio()


if __name__ == "__main__":
    main()
