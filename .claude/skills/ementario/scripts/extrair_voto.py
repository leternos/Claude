#!/usr/bin/env python3
"""Extrai o texto de um arquivo de voto (.docx, .pdf, .txt ou .md) para a saída padrão.

Uso:
    python3 scripts/extrair_voto.py entradas/voto.docx
    python3 scripts/extrair_voto.py entradas/voto.pdf > /tmp/voto.txt

Sem dependências além do que já existe na máquina: .docx é lido direto do
zip/XML, .pdf usa PyMuPDF e, na falta dele, cai para o pdftotext.
"""

import re
import subprocess
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
MC = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"


def _coletar(no, pedacos, raiz_p=True):
    """Junta o texto de um parágrafo na ordem do documento, pulando
    mc:Fallback (duplicata das caixas de texto em mc:AlternateContent);
    parágrafos aninhados (caixas de texto) viram quebras de linha."""
    if no.tag == f"{MC}Fallback":
        return
    if no.tag == f"{W}p" and not raiz_p:
        pedacos.append("\n")
    if no.tag == f"{W}t":
        pedacos.append(no.text or "")
    elif no.tag == f"{W}tab":
        pedacos.append("\t")
    elif no.tag in (f"{W}br", f"{W}cr"):
        pedacos.append("\n")
    for filho in no:
        _coletar(filho, pedacos, raiz_p=False)


def _paragrafos(raiz) -> list[str]:
    """Um parágrafo por w:p de nível superior — sem contar de novo os
    w:p aninhados em caixas de texto, já absorvidos pelo parágrafo-âncora."""
    saida = []

    def caminhar(no):
        if no.tag == f"{MC}Fallback":
            return
        if no.tag == f"{W}p":
            pedacos: list[str] = []
            _coletar(no, pedacos)
            saida.append("".join(pedacos).strip())
            return
        for filho in no:
            caminhar(filho)

    caminhar(raiz)
    return saida


def do_docx(caminho: Path) -> str:
    with zipfile.ZipFile(caminho) as z:
        raiz = ElementTree.fromstring(z.read("word/document.xml"))
        paragrafos = _paragrafos(raiz)
        # notas de rodapé/fim carregam citações substantivas do voto
        for parte, rotulo in (("word/footnotes.xml", "NOTAS DE RODAPÉ"),
                              ("word/endnotes.xml", "NOTAS DE FIM")):
            if parte not in z.namelist():
                continue
            raiz_notas = ElementTree.fromstring(z.read(parte))
            notas = []
            for nota in raiz_notas:
                if nota.get(f"{W}type") in ("separator", "continuationSeparator"):
                    continue
                notas += _paragrafos(nota)
            notas = [n for n in notas if n]
            if notas:
                paragrafos.append(f"[{rotulo}]")
                paragrafos += notas
    return "\n\n".join(p for p in paragrafos if p)


def do_pdf(caminho: Path) -> str:
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return subprocess.run(
            ["pdftotext", "-layout", str(caminho), "-"],
            capture_output=True, text=True, check=True,
        ).stdout
    with fitz.open(caminho) as doc:
        return "\n\n".join(pagina.get_text() for pagina in doc)


def extrair(caminho: Path) -> str:
    sufixo = caminho.suffix.lower()
    if sufixo == ".docx":
        texto = do_docx(caminho)
    elif sufixo == ".pdf":
        texto = do_pdf(caminho)
    elif sufixo in (".txt", ".md"):
        texto = caminho.read_text(encoding="utf-8", errors="replace")
    else:
        raise SystemExit(f"formato não suportado: {sufixo} (use .docx, .pdf, .txt ou .md)")
    # normaliza espaçamento sem colar parágrafos
    texto = texto.replace("\r\n", "\n").replace("\xa0", " ")
    return re.sub(r"\n{3,}", "\n\n", texto).strip()


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    caminho = Path(sys.argv[1])
    if not caminho.is_file():
        raise SystemExit(f"arquivo não encontrado: {caminho}")
    texto = extrair(caminho)
    if not texto:
        if caminho.suffix.lower() == ".pdf":
            raise SystemExit(f"nenhum texto extraído de {caminho} — o arquivo pode ser um PDF digitalizado (imagem)")
        raise SystemExit(f"nenhum texto extraído de {caminho} — o arquivo está vazio")
    sys.stdout.write(texto + "\n")


if __name__ == "__main__":
    main()
