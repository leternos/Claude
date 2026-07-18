"""Comparador de arquivos — FastAPI com interface HTML estilo Word.

Execução (a partir da pasta ``diff/``)::

    uvicorn main:app --reload

Depois abra http://127.0.0.1:8000 no navegador.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from diffing import comparar_textos

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(
    title="Comparador de Arquivos",
    description="Compara dois arquivos de texto com marcação estilo Word.",
)

# Limite por arquivo; diffs de arquivos maiores que isso ficam lentos e a
# página de resultado, gigante.
TAMANHO_MAXIMO = 5 * 1024 * 1024


def _decodificar(dados: bytes) -> str | None:
    """Decodifica bytes de texto; devolve ``None`` para conteúdo binário."""
    if b"\x00" in dados:
        return None
    for codificacao in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return dados.decode(codificacao)
        except UnicodeDecodeError:
            continue
    return None


def _pagina_inicial(request: Request, erro: str | None = None, status: int = 200):
    return templates.TemplateResponse(
        request, "index.html", {"erro": erro}, status_code=status
    )


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return _pagina_inicial(request)


@app.post("/comparar", response_class=HTMLResponse)
async def comparar(
    request: Request,
    original: UploadFile = File(...),
    modificado: UploadFile = File(...),
):
    dados_original = await original.read()
    dados_modificado = await modificado.read()

    for arquivo, dados in ((original, dados_original), (modificado, dados_modificado)):
        if len(dados) > TAMANHO_MAXIMO:
            return _pagina_inicial(
                request,
                erro=f"O arquivo “{arquivo.filename}” passa do limite de 5 MB.",
                status=413,
            )

    texto_original = _decodificar(dados_original)
    texto_modificado = _decodificar(dados_modificado)
    if texto_original is None or texto_modificado is None:
        nome = original.filename if texto_original is None else modificado.filename
        return _pagina_inicial(
            request,
            erro=f"O arquivo “{nome}” não parece ser texto. "
            "Envie arquivos de texto (txt, md, código, csv…).",
            status=400,
        )

    comparacao = comparar_textos(texto_original, texto_modificado)
    return templates.TemplateResponse(
        request,
        "resultado.html",
        {
            "nome_original": original.filename or "original",
            "nome_modificado": modificado.filename or "modificado",
            "comparacao": comparacao,
        },
    )
