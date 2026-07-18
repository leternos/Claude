"""Testes do motor de comparação. Rode com ``python test_diffing.py`` ou pytest."""

from diffing import comparar_textos


def _tipos_unificado(comparacao):
    return [linha.tipo for linha in comparacao.unificado]


def test_arquivos_identicos():
    c = comparar_textos("a\nb\nc", "a\nb\nc")
    assert c.identicos
    assert _tipos_unificado(c) == ["igual", "igual", "igual"]
    assert c.estatisticas.iguais == 3


def test_linha_adicionada():
    c = comparar_textos("a\nc", "a\nb\nc")
    assert _tipos_unificado(c) == ["igual", "add", "igual"]
    assert c.estatisticas.adicionadas == 1
    nova = c.unificado[1]
    assert nova.num_original is None
    assert nova.num_modificado == 2
    assert nova.segmentos[0].tipo == "add"
    assert nova.segmentos[0].texto == "b"


def test_linha_removida():
    c = comparar_textos("a\nb\nc", "a\nc")
    assert _tipos_unificado(c) == ["igual", "del", "igual"]
    assert c.estatisticas.removidas == 1
    removida = c.unificado[1]
    assert removida.num_original == 2
    assert removida.num_modificado is None


def test_linha_alterada_marca_palavras():
    c = comparar_textos("o gato subiu no telhado", "o gato pulou no muro")
    assert _tipos_unificado(c) == ["alterada"]
    assert c.estatisticas.alteradas == 1
    segmentos = c.unificado[0].segmentos
    removidos = "".join(s.texto for s in segmentos if s.tipo == "del")
    adicionados = "".join(s.texto for s in segmentos if s.tipo == "add")
    assert "subiu" in removidos and "telhado" in removidos
    assert "pulou" in adicionados and "muro" in adicionados
    # o que não mudou continua sem marcação
    iguais = "".join(s.texto for s in segmentos if s.tipo == "igual")
    assert "gato" in iguais


def test_linhas_muito_diferentes_viram_del_e_add():
    c = comparar_textos("import os", "def calcular_media(valores):")
    assert _tipos_unificado(c) == ["del", "add"]
    # no lado a lado, o par fica na mesma linha da tabela
    assert len(c.lado_a_lado) == 1
    par = c.lado_a_lado[0]
    assert par.original.tipo == "del"
    assert par.modificado.tipo == "add"


def test_lado_a_lado_alinha_com_celulas_vazias():
    c = comparar_textos("a", "a\nb")
    assert len(c.lado_a_lado) == 2
    assert c.lado_a_lado[1].original.tipo == "vazia"
    assert c.lado_a_lado[1].modificado.tipo == "add"


def test_numeracao_das_linhas():
    c = comparar_textos("x\ny", "x\nnovo\ny")
    numeros = [(l.num_original, l.num_modificado) for l in c.unificado]
    assert numeros == [(1, 1), (None, 2), (2, 3)]


def test_reconstrucao_preserva_texto():
    original = "def soma(a, b):\n    return a + b\n"
    modificado = "def soma(a, b, c=0):\n    return a + b + c\n"
    c = comparar_textos(original, modificado)
    for linha in c.unificado:
        sem_add = "".join(s.texto for s in linha.segmentos if s.tipo != "add")
        sem_del = "".join(s.texto for s in linha.segmentos if s.tipo != "del")
        if linha.num_original is not None:
            assert sem_add == original.splitlines()[linha.num_original - 1]
        if linha.num_modificado is not None:
            assert sem_del == modificado.splitlines()[linha.num_modificado - 1]


def test_alinhamento_por_similaridade_em_bloco_replace():
    # A linha "Próxima reunião" mudou de posição dentro do bloco alterado e
    # deve casar com a versão nova dela, não com a linha que ocupa sua posição.
    original = "A equipe atingiu a meta.\nO faturamento foi de R$ 120 mil.\nPróxima reunião: dia 10."
    modificado = "A equipe superou a meta.\nPróxima reunião: dia 15.\nNovo item: contratar."
    c = comparar_textos(original, modificado)
    alteradas = [l for l in c.unificado if l.tipo == "alterada"]
    pares = {(l.num_original, l.num_modificado) for l in alteradas}
    assert (1, 1) in pares
    assert (3, 2) in pares  # "dia 10" -> "dia 15", apesar do deslocamento
    assert c.estatisticas.removidas == 1  # faturamento
    assert c.estatisticas.adicionadas == 1  # novo item


def test_texto_vazio():
    c = comparar_textos("", "a\nb")
    assert c.estatisticas.adicionadas == 2
    c2 = comparar_textos("", "")
    assert c2.identicos


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
