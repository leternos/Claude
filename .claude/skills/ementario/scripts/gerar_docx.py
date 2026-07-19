#!/usr/bin/env python3
"""Converte a ementa em Markdown (saidas/*.md) para .docx pronto para colar no voto.

Uso:
    python3 scripts/gerar_docx.py saidas/ementa-020701-4-25.md
    python3 scripts/gerar_docx.py saidas/ementa-020701-4-25.md -o /caminho/Ementa.docx

Aproveita apenas o bloco da ementa — do cabeçalho "EMENTA:" até o último item do
DISPOSITIVO. Notas de trabalho ("## Pendência", "## Fonte") ficam de fora.

Formatação: Times New Roman 12, parágrafos justificados, rótulos em negrito.
Sem dependências: o .docx é escrito diretamente como zip/OOXML.
"""

import argparse
import re
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>"""

RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:docDefaults><w:rPrDefault><w:rPr>
<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/>
<w:sz w:val="24"/><w:szCs w:val="24"/><w:lang w:val="pt-BR"/>
</w:rPr></w:rPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/>
<w:pPr><w:jc w:val="both"/><w:spacing w:after="180" w:line="276" w:lineRule="auto"/></w:pPr>
</w:style></w:styles>"""


def runs(texto: str) -> str:
    """Converte **negrito** em runs OOXML."""
    saida = []
    for pedaco in re.split(r"(\*\*.+?\*\*)", texto):
        if not pedaco:
            continue
        negrito = pedaco.startswith("**") and pedaco.endswith("**")
        conteudo = pedaco[2:-2] if negrito else pedaco
        rpr = "<w:rPr><w:b/></w:rPr>" if negrito else ""
        saida.append(
            f'<w:r>{rpr}<w:t xml:space="preserve">{escape(conteudo)}</w:t></w:r>'
        )
    return "".join(saida)


def recortar_ementa(md: str) -> list[str]:
    """Do cabeçalho EMENTA: até o fim do DISPOSITIVO."""
    linhas = md.replace("\r\n", "\n").split("\n")
    try:
        inicio = next(i for i, l in enumerate(linhas) if l.lstrip("*").startswith("EMENTA:"))
    except StopIteration:
        raise SystemExit("não encontrei o cabeçalho 'EMENTA:' no arquivo")
    fim = len(linhas)
    for i in range(inicio, len(linhas)):
        if re.match(r"\s*#{1,6}\s", linhas[i]):  # notas de trabalho — não entram
            fim = i
            break
    corpo = linhas[inicio:fim]
    while corpo and corpo[-1].strip() in ("", "---"):
        corpo.pop()

    # Cada parágrafo começa num rótulo (EMENTA:/CASO.../RAZÕES.../DISPOSITIVO) ou
    # num item numerado ("1. ..."); linhas de continuação (item que vaza para a
    # linha seguinte) são anexadas ao parágrafo atual. Assim a ementa não colapsa
    # num bloco só quando os itens vêm separados apenas por quebra de linha.
    def inicia_paragrafo(linha: str) -> bool:
        nu = linha.lstrip("*").strip()
        return bool(
            re.match(r"\d+\.\s", nu)
            or re.match(r"EMENTA:", nu)
            or re.match(r"(CASO EM EXAME|RAZÕES DE DECIDIR|DISPOSITIVO)", nu)
        )

    paragrafos, atual = [], []
    for linha in corpo:
        if not linha.strip() or linha.strip() == "---":
            if atual:
                paragrafos.append(" ".join(atual))
                atual = []
            continue
        if atual and inicia_paragrafo(linha):
            paragrafos.append(" ".join(atual))
            atual = []
        atual.append(linha.strip())
    if atual:
        paragrafos.append(" ".join(atual))

    # negrito desequilibrado viraria '**' literal no documento final
    for p in paragrafos:
        if p.count("**") % 2:
            raise SystemExit(f"negrito '**' desequilibrado no parágrafo: {p[:70]}…")
    return paragrafos


def gerar(paragrafos: list[str], destino: Path) -> None:
    corpo = "".join(f"<w:p>{runs(p)}</w:p>" for p in paragrafos)
    documento = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{corpo}"
        '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1701" w:right="1134" w:bottom="1134" w:left="1701"/></w:sectPr>'
        "</w:body></w:document>"
    )
    destino.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr("word/_rels/document.xml.rels", DOC_RELS)
        z.writestr("word/styles.xml", STYLES)
        z.writestr("word/document.xml", documento)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("markdown", type=Path)
    ap.add_argument("-o", "--saida", type=Path)
    args = ap.parse_args()

    paragrafos = recortar_ementa(args.markdown.read_text(encoding="utf-8"))
    # uma ementa mínima tem cabeçalho + 3 rótulos + itens: menos que 6 parágrafos
    # é sinal de colapso (itens colados num bloco só por falta de quebras)
    if len(paragrafos) < 6:
        raise SystemExit(
            f"ementa suspeita de colapso: só {len(paragrafos)} parágrafo(s) — "
            "confira as quebras de linha do markdown"
        )
    destino = args.saida or args.markdown.with_suffix(".docx")
    gerar(paragrafos, destino)

    # revalidação: o arquivo abre, tem os quatro blocos e termina no dispositivo
    with zipfile.ZipFile(destino) as z:
        texto = z.read("word/document.xml").decode("utf-8")
    faltando = [
        r for r in ("EMENTA:", "CASO EM EXAME", "RAZÕES DE DECIDIR", "DISPOSITIVO")
        if escape(r) not in texto
    ]
    if faltando:
        raise SystemExit(f"gravação incompleta — blocos ausentes: {', '.join(faltando)}")
    print(f"{destino} — {destino.stat().st_size} bytes, {len(paragrafos)} parágrafos")


if __name__ == "__main__":
    main()
