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


def do_docx(caminho: Path) -> str:
    with zipfile.ZipFile(caminho) as z:
        xml = z.read("word/document.xml")
    raiz = ElementTree.fromstring(xml)
    paragrafos = []
    for p in raiz.iter(f"{W}p"):
        pedacos = []
        for no in p.iter():
            if no.tag == f"{W}t":
                pedacos.append(no.text or "")
            elif no.tag in (f"{W}tab",):
                pedacos.append("\t")
            elif no.tag in (f"{W}br", f"{W}cr"):
                pedacos.append("\n")
        paragrafos.append("".join(pedacos).strip())
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
        raise SystemExit(f"formato não suportado: {sufixo} (use .docx, .pdf, .txt)")
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
        raise SystemExit(f"nenhum texto extraído de {caminho} — o arquivo pode ser um PDF digitalizado (imagem)")
    sys.stdout.write(texto + "\n")


if __name__ == "__main__":
    main()
