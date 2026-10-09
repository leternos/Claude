"""Testes da extração de texto (txt, docx, doc).

Os arquivos em ``testdata/`` foram gerados pelo LibreOffice a partir de
``contrato_v1.txt``, então a extração dos três formatos deve devolver
exatamente as mesmas linhas. Rode com ``python test_extracao.py`` ou pytest.
"""

import io
import zipfile
from pathlib import Path

from extracao import ExtracaoErro, extrair_docx, extrair_texto

TESTDATA = Path(__file__).resolve().parent / "testdata"


def _linhas_do_contrato():
    return (TESTDATA / "contrato_v1.txt").read_text(encoding="utf-8").splitlines()


def _docx_minimo(document_xml: str) -> bytes:
    """Monta um .docx mínimo em memória com o document.xml dado."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as pacote:
        pacote.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            "</Types>",
        )
        pacote.writestr("word/document.xml", document_xml)
    return buffer.getvalue()


def test_txt_extrai_igual():
    dados = (TESTDATA / "contrato_v1.txt").read_bytes()
    assert extrair_texto("contrato_v1.txt", dados).splitlines() == _linhas_do_contrato()


def test_docx_do_libreoffice():
    dados = (TESTDATA / "contrato_v1.docx").read_bytes()
    assert extrair_texto("contrato_v1.docx", dados).splitlines() == _linhas_do_contrato()


def test_doc_do_libreoffice():
    dados = (TESTDATA / "contrato_v1.doc").read_bytes()
    assert extrair_texto("contrato_v1.doc", dados).splitlines() == _linhas_do_contrato()


def test_docx_tab_e_quebra_de_linha():
    xml = (
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        "<w:p><w:r><w:t>a</w:t><w:tab/><w:t>b</w:t><w:br/><w:t>c</w:t></w:r></w:p>"
        "<w:p><w:r><w:t xml:space=\"preserve\">  espaços  </w:t></w:r></w:p>"
        "</w:body></w:document>"
    )
    assert extrair_docx(_docx_minimo(xml)) == "a\tb\nc\n  espaços  "


def test_docx_ignora_tab_de_estilo():
    # <w:tab> dentro de <w:tabs> (definição de parada de tabulação) não é texto.
    xml = (
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body><w:p>"
        '<w:pPr><w:tabs><w:tab w:val="left" w:pos="708"/></w:tabs></w:pPr>'
        "<w:r><w:t>texto</w:t></w:r>"
        "</w:p></w:body></w:document>"
    )
    assert extrair_docx(_docx_minimo(xml)) == "texto"


def test_zip_que_nao_e_word():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as pacote:
        pacote.writestr("qualquer.txt", "oi")
    try:
        extrair_texto("planilha.xlsx", buffer.getvalue())
    except ExtracaoErro as exc:
        assert "ZIP" in str(exc)
    else:
        raise AssertionError("deveria recusar ZIP que não é docx")


def test_binario_desconhecido():
    try:
        extrair_texto("imagem.png", b"\x89PNG\r\n\x1a\n\x00\x00")
    except ExtracaoErro as exc:
        assert "docx" in str(exc)
    else:
        raise AssertionError("deveria recusar binário desconhecido")


if __name__ == "__main__":
    falhas = 0
    for nome, funcao in sorted(globals().items()):
        if nome.startswith("test_") and callable(funcao):
            try:
                funcao()
                print(f"ok   {nome}")
            except AssertionError as exc:
                falhas += 1
                print(f"FALHOU {nome}: {exc}")
    raise SystemExit(1 if falhas else 0)
