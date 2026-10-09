"""Motor de comparação de textos com saída no estilo "Controlar Alterações" do Word.

A comparação acontece em dois níveis:

1. Nível de linha — ``difflib.SequenceMatcher`` alinha as linhas dos dois
   arquivos e classifica cada uma como igual, adicionada, removida ou alterada.
2. Nível de palavra — dentro de um par de linhas alteradas, um segundo
   ``SequenceMatcher`` sobre os tokens (palavras e espaços) marca exatamente
   quais trechos saíram (vermelho tachado) e quais entraram (verde sublinhado),
   como o Word faz ao comparar documentos.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field

# Palavras e sequências de espaço viram tokens separados, preservando o
# espaçamento original na reconstrução da linha.
_TOKEN_RE = re.compile(r"\s+|\S+")

# Abaixo desta similaridade, um par de linhas casadas num bloco "replace" é
# tratado como remoção + adição inteiras — um diff palavra a palavra entre
# linhas muito diferentes só gera ruído visual.
_LIMIAR_SIMILARIDADE = 0.4

# Acima deste número de combinações num bloco "replace", o alinhamento por
# similaridade (quadrático) sai caro demais e caímos no pareamento posicional.
_MAX_COMBINACOES = 40_000


@dataclass
class Segmento:
    """Trecho contíguo de uma linha com uma única marcação."""

    tipo: str  # "igual" | "add" | "del"
    texto: str


@dataclass
class LinhaUnificada:
    """Linha da visão unificada (documento marcado)."""

    tipo: str  # "igual" | "add" | "del" | "alterada"
    num_original: int | None
    num_modificado: int | None
    segmentos: list[Segmento] = field(default_factory=list)


@dataclass
class Celula:
    """Metade de uma linha da visão lado a lado."""

    tipo: str  # "igual" | "add" | "del" | "alterada" | "vazia"
    numero: int | None = None
    segmentos: list[Segmento] = field(default_factory=list)


@dataclass
class LinhaLadoALado:
    original: Celula
    modificado: Celula


@dataclass
class Estatisticas:
    adicionadas: int = 0
    removidas: int = 0
    alteradas: int = 0
    iguais: int = 0

    @property
    def total_mudancas(self) -> int:
        return self.adicionadas + self.removidas + self.alteradas


@dataclass
class Comparacao:
    unificado: list[LinhaUnificada]
    lado_a_lado: list[LinhaLadoALado]
    estatisticas: Estatisticas

    @property
    def identicos(self) -> bool:
        return self.estatisticas.total_mudancas == 0


def _tokenizar(linha: str) -> list[str]:
    return _TOKEN_RE.findall(linha)


def _juntar(tokens: list[str]) -> str:
    return "".join(tokens)


def _segmentos_inline(
    original: str, modificado: str
) -> tuple[list[Segmento], list[Segmento], list[Segmento]]:
    """Diff palavra a palavra entre duas linhas.

    Retorna três listas de segmentos: a linha mesclada (visão unificada, com
    remoções e adições intercaladas), a linha original (só "igual"/"del") e a
    linha modificada (só "igual"/"add").
    """
    matcher = difflib.SequenceMatcher(
        a=_tokenizar(original), b=_tokenizar(modificado), autojunk=False
    )
    mesclada: list[Segmento] = []
    lado_original: list[Segmento] = []
    lado_modificado: list[Segmento] = []
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        trecho_a = _juntar(matcher.a[i1:i2])
        trecho_b = _juntar(matcher.b[j1:j2])
        if op == "equal":
            mesclada.append(Segmento("igual", trecho_a))
            lado_original.append(Segmento("igual", trecho_a))
            lado_modificado.append(Segmento("igual", trecho_b))
        elif op == "delete":
            mesclada.append(Segmento("del", trecho_a))
            lado_original.append(Segmento("del", trecho_a))
        elif op == "insert":
            mesclada.append(Segmento("add", trecho_b))
            lado_modificado.append(Segmento("add", trecho_b))
        else:  # replace
            mesclada.append(Segmento("del", trecho_a))
            mesclada.append(Segmento("add", trecho_b))
            lado_original.append(Segmento("del", trecho_a))
            lado_modificado.append(Segmento("add", trecho_b))
    return mesclada, lado_original, lado_modificado


class _Montador:
    """Acumula as duas visões e as estatísticas durante a varredura."""

    def __init__(self) -> None:
        self.unificado: list[LinhaUnificada] = []
        self.lado_a_lado: list[LinhaLadoALado] = []
        self.estatisticas = Estatisticas()

    def igual(self, texto: str, num_o: int, num_m: int) -> None:
        seg = [Segmento("igual", texto)]
        self.unificado.append(LinhaUnificada("igual", num_o, num_m, seg))
        self.lado_a_lado.append(
            LinhaLadoALado(Celula("igual", num_o, seg), Celula("igual", num_m, seg))
        )
        self.estatisticas.iguais += 1

    def remocao(self, texto: str, num_o: int) -> None:
        seg = [Segmento("del", texto)]
        self.unificado.append(LinhaUnificada("del", num_o, None, seg))
        self.lado_a_lado.append(
            LinhaLadoALado(Celula("del", num_o, seg), Celula("vazia"))
        )
        self.estatisticas.removidas += 1

    def adicao(self, texto: str, num_m: int) -> None:
        seg = [Segmento("add", texto)]
        self.unificado.append(LinhaUnificada("add", None, num_m, seg))
        self.lado_a_lado.append(
            LinhaLadoALado(Celula("vazia"), Celula("add", num_m, seg))
        )
        self.estatisticas.adicionadas += 1

    def alteracao(self, original: str, modificado: str, num_o: int, num_m: int) -> None:
        mesclada, lado_o, lado_m = _segmentos_inline(original, modificado)
        self.unificado.append(LinhaUnificada("alterada", num_o, num_m, mesclada))
        self.lado_a_lado.append(
            LinhaLadoALado(
                Celula("alterada", num_o, lado_o),
                Celula("alterada", num_m, lado_m),
            )
        )
        self.estatisticas.alteradas += 1

    def troca_integral(self, original: str, modificado: str, num_o: int, num_m: int) -> None:
        """Par de linhas dessemelhantes: remoção e adição inteiras, lado a lado."""
        seg_del = [Segmento("del", original)]
        seg_add = [Segmento("add", modificado)]
        self.unificado.append(LinhaUnificada("del", num_o, None, seg_del))
        self.unificado.append(LinhaUnificada("add", None, num_m, seg_add))
        self.lado_a_lado.append(
            LinhaLadoALado(Celula("del", num_o, seg_del), Celula("add", num_m, seg_add))
        )
        self.estatisticas.removidas += 1
        self.estatisticas.adicionadas += 1


def _ratio(a: str, b: str) -> float:
    return difflib.SequenceMatcher(a=a, b=b, autojunk=False).ratio()


def _replace_posicional(
    montador: _Montador, linhas_o: list[str], linhas_m: list[str],
    i1: int, i2: int, j1: int, j2: int,
) -> None:
    """Pareia linha a linha pela posição; sobras viram remoções/adições."""
    for k in range(max(i2 - i1, j2 - j1)):
        tem_o = i1 + k < i2
        tem_m = j1 + k < j2
        if tem_o and tem_m:
            linha_o = linhas_o[i1 + k]
            linha_m = linhas_m[j1 + k]
            if _ratio(linha_o, linha_m) >= _LIMIAR_SIMILARIDADE:
                montador.alteracao(linha_o, linha_m, i1 + k + 1, j1 + k + 1)
            else:
                montador.troca_integral(linha_o, linha_m, i1 + k + 1, j1 + k + 1)
        elif tem_o:
            montador.remocao(linhas_o[i1 + k], i1 + k + 1)
        else:
            montador.adicao(linhas_m[j1 + k], j1 + k + 1)


def _replace_por_similaridade(
    montador: _Montador, linhas_o: list[str], linhas_m: list[str],
    i1: int, i2: int, j1: int, j2: int,
) -> None:
    """Alinha um bloco "replace" pelo par de linhas mais parecido.

    Mesma ideia do ``difflib.Differ``: acha o melhor par, emite o que vem
    antes dele recursivamente, marca o par como alteração e segue com o que
    vem depois. Assim "Próxima reunião: dia 10" casa com "Próxima reunião:
    dia 15" mesmo que as linhas tenham mudado de posição dentro do bloco.
    """
    if i1 >= i2 and j1 >= j2:
        return
    if i1 >= i2:
        for j in range(j1, j2):
            montador.adicao(linhas_m[j], j + 1)
        return
    if j1 >= j2:
        for i in range(i1, i2):
            montador.remocao(linhas_o[i], i + 1)
        return
    if (i2 - i1) * (j2 - j1) > _MAX_COMBINACOES:
        _replace_posicional(montador, linhas_o, linhas_m, i1, i2, j1, j2)
        return

    melhor_ratio, melhor_i, melhor_j = -1.0, i1, j1
    for i in range(i1, i2):
        for j in range(j1, j2):
            r = _ratio(linhas_o[i], linhas_m[j])
            if r > melhor_ratio:
                melhor_ratio, melhor_i, melhor_j = r, i, j

    if melhor_ratio < _LIMIAR_SIMILARIDADE:
        _replace_posicional(montador, linhas_o, linhas_m, i1, i2, j1, j2)
        return

    _replace_por_similaridade(montador, linhas_o, linhas_m, i1, melhor_i, j1, melhor_j)
    if linhas_o[melhor_i] == linhas_m[melhor_j]:
        montador.igual(linhas_o[melhor_i], melhor_i + 1, melhor_j + 1)
    else:
        montador.alteracao(
            linhas_o[melhor_i], linhas_m[melhor_j], melhor_i + 1, melhor_j + 1
        )
    _replace_por_similaridade(montador, linhas_o, linhas_m, melhor_i + 1, i2, melhor_j + 1, j2)


def comparar_textos(texto_original: str, texto_modificado: str) -> Comparacao:
    """Compara dois textos e devolve as visões unificada e lado a lado."""
    linhas_o = texto_original.splitlines()
    linhas_m = texto_modificado.splitlines()
    matcher = difflib.SequenceMatcher(a=linhas_o, b=linhas_m, autojunk=False)
    montador = _Montador()

    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == "equal":
            for k in range(i2 - i1):
                montador.igual(linhas_o[i1 + k], i1 + k + 1, j1 + k + 1)
        elif op == "delete":
            for i in range(i1, i2):
                montador.remocao(linhas_o[i], i + 1)
        elif op == "insert":
            for j in range(j1, j2):
                montador.adicao(linhas_m[j], j + 1)
        else:
            _replace_por_similaridade(montador, linhas_o, linhas_m, i1, i2, j1, j2)

    return Comparacao(montador.unificado, montador.lado_a_lado, montador.estatisticas)
