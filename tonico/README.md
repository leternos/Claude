# tonico — estudo de estilo de escrita

Pipeline de estilometria jurídica para estudar a escrita de **Antonio Carlos
Monteiro da Silva Filho (OAB/SP 124.536)** a partir de peças, artigos,
comentários e publicações.

Só usa a biblioteca-padrão do Python 3.10+. Para extrair PDF, instale
`pip install pypdf` (ou tenha o binário `pdftotext` no sistema).

## Uso

```bash
# 1. Gera links de busca prontos (Google, JusBrasil, Escavador, e-SAJ TJSP...)
python3 tonico.py buscar

# 2. Salve as peças/artigos encontrados em tonico/corpus/  (PDF, DOCX, HTML ou TXT)
#    — ou liste URLs, uma por linha, em tonico/corpus/fontes.txt

# 3. Roda tudo: ingestão -> análise -> relatório
python3 tonico.py tudo
```

Também dá para rodar cada etapa separada (`ingerir`, `analisar`, `relatorio`)
e passar arquivos, pastas ou URLs direto: `python3 tonico.py ingerir peca.pdf
https://exemplo.com/artigo`.

## O que sai

- **`banco/estilo.db`** — banco SQLite com os textos e todas as tabelas de
  análise (`documentos`, `palavras`, `ngramas`, `citacoes`, `expressoes`,
  `metricas`), pronto para consultas próprias.
- **`relatorios/relatorio.md`** — relatório com:
  1. inventário do corpus;
  2. ranking das palavras mais usadas (sem stopwords e sem a assinatura);
  3. bigramas/trigramas característicos;
  4. métricas de estilo (palavras por frase, riqueza lexical, palavras longas);
  5. heurísticas comportamentais (assertividade × cautela, combatividade,
     cortesia forense, voz em 1ª pessoa singular × plural, conectivos preferidos);
  6. embasamento: citações de legislação, jurisprudência e doutrina (ABNT);
  7. filosofia: princípios invocados, autores/pensadores, correntes e métodos;
  8. tendências por ano (quando a data é detectável na peça ou no nome do arquivo).

## Avisos

- `corpus/`, `banco/` e `relatorios/` estão no `.gitignore`: documentos de
  cliente e resultados **não sobem** para o repositório.
- Busca automática em tribunais/JusBrasil exige login ou captcha; por isso o
  comando `buscar` gera os links e a coleta final é manual.
- As heurísticas são baseadas em léxico e regex — revise criticamente; falsos
  positivos são possíveis.

## Detecção de datas

Para a seção de tendências, o script procura a data por extenso no fim da peça
("São Paulo, 10 de março de 2021") ou um ano no nome do arquivo
(`artigo_2023.pdf`).
