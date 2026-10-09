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

## Versão estática (sem servidor)

O arquivo [`comparador.html`](comparador.html) é uma **versão exportada do
app inteiro num único HTML**: o motor de comparação foi portado de Python
para JavaScript e roda 100% no navegador — os arquivos nunca saem da sua
máquina. Basta abrir o arquivo com dois cliques (ou hospedá-lo em qualquer
lugar, como GitHub Pages). Mesma interface, mesmas cores, mesmas duas visões.

A paridade entre os dois motores é garantida por vetores de teste: a saída
do motor Python (`diffing.py`) é comparada campo a campo com a do motor JS
para os mesmos pares de entrada (16 casos, incluindo CRLF, acentos, newline
final e alinhamento por similaridade).

## O que ele aceita

- Arquivos de **texto** em geral: `.txt`, `.md`, código-fonte, `.csv`, etc.
  (UTF-8 com ou sem BOM, caindo para Latin-1).
- Documentos do **Word**: `.docx` (Word 2007+) e `.doc` (Word 97–2003).
  O texto é extraído — um parágrafo por linha, preservando tabs e quebras —
  e comparado como os demais formatos. Dá inclusive para comparar um `.doc`
  com um `.docx` ou com um `.txt`.
- Até **5 MB** por arquivo.
- Outros binários (`.pdf`, imagens…) são rejeitados com mensagem amigável.

A extração fica em [`extracao.py`](extracao.py): `.docx` é lido do
`word/document.xml` dentro do pacote ZIP; `.doc` segue a *piece table* do
formato Word 97 (fluxos `WordDocument`/`0Table`-`1Table` no contêiner OLE,
com trechos em CP-1252 ou UTF-16LE), como fazem o antiword e o wvware. A
versão estática tem o mesmo suporte, portado para JavaScript — incluindo um
leitor de ZIP (com `DecompressionStream`) e de contêiner OLE/CFB.

## Estrutura

```
diff/
├── main.py            # rotas FastAPI (upload + renderização)
├── diffing.py         # motor de comparação (difflib, linha + palavra)
├── extracao.py        # extração de texto: txt, .docx e .doc
├── comparador.html    # versão estática: app completo num único HTML (JS)
├── templates/
│   ├── base.html      # layout e CSS estilo Word
│   ├── index.html     # formulário de upload com arrastar-e-soltar
│   └── resultado.html # visões "Documento marcado" e "Lado a lado"
├── test_diffing.py    # testes do motor de comparação
├── test_extracao.py   # testes da extração (com fixtures reais em testdata/)
├── testdata/          # contrato fictício em .txt, .docx e .doc (LibreOffice)
└── requirements.txt
```

## Testes

```bash
cd diff
python test_diffing.py    # motor de comparação
python test_extracao.py   # extração txt/docx/doc (ou: pytest)
```
