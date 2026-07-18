# Comparador de Arquivos (`/diff`)

Aplicação **FastAPI** com interface HTML para comparar dois arquivos de texto,
com o resultado marcado no estilo **"Controlar Alterações" do Word**:

- <span style="color:#c43e1c">~~vermelho tachado~~</span> — texto que **saiu** do arquivo original;
- <span style="color:#107c41">verde sublinhado</span> — texto que **entrou** no arquivo modificado;
- fundo amarelo com barra de revisão — **linhas alteradas**, com a diferença
  marcada **palavra a palavra** dentro da linha;
- barras de revisão coloridas na margem esquerda, como no Word.

Há duas visões, alternáveis por abas:

1. **Documento marcado** — visão unificada, com remoções e adições
   intercaladas no mesmo texto (como o Word exibe um documento comparado);
2. **Lado a lado** — original à esquerda, modificado à direita, com linhas
   alinhadas e numeradas.

## Como rodar

```bash
cd diff
pip install -r requirements.txt
uvicorn main:app --reload
```

Depois abra <http://127.0.0.1:8000>, escolha (ou arraste) os dois arquivos e
clique em **Comparar**.

## O que ele aceita

- Arquivos de **texto** em geral: `.txt`, `.md`, código-fonte, `.csv`, etc.
- Codificações UTF-8 (com ou sem BOM) e Latin-1.
- Até **5 MB** por arquivo.
- Arquivos binários são rejeitados com uma mensagem amigável (formatos como
  `.docx`/`.pdf` precisariam de extração de texto antes — não é o caso aqui).

## Estrutura

```
diff/
├── main.py            # rotas FastAPI (upload + renderização)
├── diffing.py         # motor de comparação (difflib, linha + palavra)
├── templates/
│   ├── base.html      # layout e CSS estilo Word
│   ├── index.html     # formulário de upload com arrastar-e-soltar
│   └── resultado.html # visões "Documento marcado" e "Lado a lado"
├── test_diffing.py    # testes do motor de comparação
└── requirements.txt
```

## Testes

```bash
cd diff
python test_diffing.py   # ou: pytest test_diffing.py
```
