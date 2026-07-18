"""Extração de texto de arquivos enviados: texto puro, .docx e .doc.

- ``.docx`` (Word 2007+): pacote ZIP; o texto vem de ``word/document.xml``.
  Cada parágrafo vira uma linha; tabs e quebras dentro do parágrafo são
  preservados.
- ``.doc`` (Word 97-2003): contêiner OLE/CFB; o texto vem do fluxo
  ``WordDocument`` seguindo a *piece table* (Clx/PlcPcd) do fluxo de tabela,
  como fazem o antiword e o wvware. Trechos podem estar em CP-1252
  "comprimido" ou UTF-16LE.
- Qualquer outro conteúdo é tratado como texto puro (UTF-8 com ou sem BOM,
  caindo para Latin-1); binários desconhecidos são recusados.
"""

from __future__ import annotations

import io
import re
import struct
import zipfile
import xml.etree.ElementTree as ET

import olefile

_NS_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_MAGIC_ZIP = b"PK\x03\x04"
_MAGIC_OLE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


class ExtracaoErro(Exception):
    """Arquivo que não conseguimos transformar em texto."""


def _u16(dados: bytes, off: int) -> int:
    return struct.unpack_from("<H", dados, off)[0]


def _u32(dados: bytes, off: int) -> int:
    return struct.unpack_from("<I", dados, off)[0]


# ---------------------------------------------------------------- .docx ----

def _paragrafo_para_texto(paragrafo: ET.Element) -> str:
    partes: list[str] = []
    for run in paragrafo.iter(f"{_NS_W}r"):
        for filho in run.iter():
            tag = filho.tag
            if tag == f"{_NS_W}t":
                partes.append(filho.text or "")
            elif tag == f"{_NS_W}tab":
                partes.append("\t")
            elif tag in (f"{_NS_W}br", f"{_NS_W}cr"):
                partes.append("\n")
    return "".join(partes)


def extrair_docx(dados: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(dados)) as pacote:
            xml_documento = pacote.read("word/document.xml")
    except (zipfile.BadZipFile, KeyError) as exc:
        raise ExtracaoErro("o arquivo .docx está corrompido ou incompleto") from exc
    try:
        raiz = ET.fromstring(xml_documento)
    except ET.ParseError as exc:
        raise ExtracaoErro("o conteúdo do .docx não pôde ser lido") from exc
    linhas = [_paragrafo_para_texto(p) for p in raiz.iter(f"{_NS_W}p")]
    return "\n".join(linhas)


# ----------------------------------------------------------------- .doc ----

def _limpar_texto_doc(bruto: str) -> str:
    """Normaliza os caracteres de controle do formato Word 97.

    Campos (0x13 instrução, 0x14 separador, 0x15 fim) têm a parte de
    instrução descartada e o resultado mantido; 0x0D vira quebra de linha;
    0x07 encerra célula/linha de tabela; 0x0B é quebra de linha manual.
    """
    saida: list[str] = []
    pilha_campo: list[str] = []
    for ch in bruto:
        codigo = ord(ch)
        if codigo == 0x13:
            pilha_campo.append("instrucao")
            continue
        if codigo == 0x14:
            if pilha_campo:
                pilha_campo[-1] = "resultado"
            continue
        if codigo == 0x15:
            if pilha_campo:
                pilha_campo.pop()
            continue
        if "instrucao" in pilha_campo:
            continue
        if ch in ("\r", "\n") or codigo in (0x07, 0x0B, 0x0C):
            saida.append("\n")
        elif codigo == 0x1E:
            saida.append("-")
        elif codigo in (0x1F, 0xFEFF) or codigo < 0x20 and ch != "\t":
            continue
        else:
            saida.append(ch)
    return "".join(saida)


def extrair_doc(dados: bytes) -> str:
    try:
        ole = olefile.OleFileIO(io.BytesIO(dados))
    except OSError as exc:
        raise ExtracaoErro("o arquivo .doc está corrompido") from exc
    try:
        if not ole.exists("WordDocument"):
            raise ExtracaoErro("o arquivo não contém um documento do Word")
        word = ole.openstream("WordDocument").read()
        if len(word) < 0x200 or _u16(word, 0) != 0xA5EC:
            raise ExtracaoErro("o arquivo não parece ser um .doc do Word")
        flags = _u16(word, 0x0A)
        nome_tabela = "1Table" if flags & 0x0200 else "0Table"
        if not ole.exists(nome_tabela):
            raise ExtracaoErro("o arquivo .doc está incompleto (sem fluxo de tabela)")
        tabela = ole.openstream(nome_tabela).read()
    finally:
        ole.close()

    ccp_texto = _u32(word, 0x004C)  # caracteres do documento principal
    fc_clx = _u32(word, 0x01A2)
    lcb_clx = _u32(word, 0x01A6)
    clx = tabela[fc_clx : fc_clx + lcb_clx]

    # pula blocos Prc (0x01) até achar o Pcdt (0x02) com a piece table
    pos = 0
    while pos < len(clx) and clx[pos] == 0x01:
        pos += 3 + _u16(clx, pos + 1)
    if pos >= len(clx) or clx[pos] != 0x02:
        raise ExtracaoErro("a estrutura interna do .doc não foi reconhecida")
    lcb_plc = _u32(clx, pos + 1)
    plc = clx[pos + 5 : pos + 5 + lcb_plc]

    n = (len(plc) - 4) // 12
    if n <= 0:
        return ""
    cps = [_u32(plc, i * 4) for i in range(n + 1)]
    trechos: list[str] = []
    for i in range(n):
        fc_bruto = _u32(plc, (n + 1) * 4 + i * 8 + 2)
        quantidade = cps[i + 1] - cps[i]
        if fc_bruto & 0x40000000:  # "comprimido": CP-1252, 1 byte por char
            inicio = (fc_bruto & 0x3FFFFFFF) // 2
            trecho = word[inicio : inicio + quantidade].decode("cp1252", "replace")
        else:
            inicio = fc_bruto & 0x3FFFFFFF
            trecho = word[inicio : inicio + 2 * quantidade].decode("utf-16-le", "replace")
        trechos.append(trecho)

    return _limpar_texto_doc("".join(trechos)[:ccp_texto])


# ----------------------------------------------------------------- geral ----

def _decodificar_texto(dados: bytes) -> str | None:
    if b"\x00" in dados:
        return None
    for codificacao in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return dados.decode(codificacao)
        except UnicodeDecodeError:
            continue
    return None


def extrair_texto(nome: str, dados: bytes) -> str:
    """Devolve o texto de um upload; levanta ``ExtracaoErro`` se impossível."""
    minusculo = (nome or "").lower()
    if dados.startswith(_MAGIC_ZIP):
        try:
            return extrair_docx(dados)
        except ExtracaoErro:
            if minusculo.endswith(".docx"):
                raise
            raise ExtracaoErro(
                "o arquivo é um pacote ZIP, mas não um documento do Word"
            ) from None
    if dados.startswith(_MAGIC_OLE):
        return extrair_doc(dados)
    texto = _decodificar_texto(dados)
    if texto is None:
        raise ExtracaoErro(
            "o arquivo não parece ser texto nem documento do Word "
            "(txt, md, código, csv, docx, doc…)"
        )
    return texto
