---
name: ementario
description: >-
  Gera a EMENTA de um voto no padrão do Manual de Padronização de Ementas do TED
  OAB/SP. DISPARE AUTOMATICAMENTE, sem que o usuário peça, sempre que ele
  anexar, enviar ou apontar um arquivo .docx, .pdf, .txt ou .md cujo nome
  contenha "voto" — inclusive quando a mensagem vier só com o caminho do
  arquivo, sem texto nenhum. Entrega um único cartão no chat com a ementa
  formatada e botões Copiar e Exportar DOCX, e mais nada.
---

# Gerador de ementas — padrão TED OAB/SP

Entra um voto, sai a ementa. A skill **não interpreta o voto, não julga, não
revisa, não comenta**. Ela lê o que o voto decidiu e escreve isso no formato do
Manual.

O Manual está **embutido abaixo, por inteiro** — é o contexto de trabalho e já
está carregado no instante em que a skill dispara. **Não leia
`references/manual-ementa-ted.md` nem nenhum outro arquivo de manual em runtime**:
as regras canônicas são as desta página. O arquivo em `references/` é apenas
lastro de arquivo; a versão vigente é a inline.

## Escopo — o que NÃO fazer

- Não analisar o mérito, não avaliar a prova, não conferir a dosimetria.
- Não apontar contradições, erros, lacunas ou sugestões de melhoria do voto.
- Não resumir o voto, não explicar a ementa, não comentar o que foi feito.
- Não acrescentar fundamento, precedente, norma ou verbete que o voto não traga.
- Não perguntar nada antes de gerar (única exceção: extração vazia de PDF
  digitalizado — peça o .docx e pare). Havendo dúvida sobre um elemento,
  escreva `[VERIFICAR]` no lugar e siga.

---

## MANUAL DE PADRONIZAÇÃO — TED/SP (abr. 2025) — pré-carregado

Base: Manual do TED/SP (Pres. Guilherme Magri de Carvalho, abr. 2025), alinhado
ao Manual de Ementas do CNJ (2024, "linguagem simples") e ao Provimento
228/2024 (perspectiva de gênero). Meta: clareza, segurança jurídica e leitura
por IA dos tribunais. Esta padronização **substitui** qualquer formato anterior
e prevalece sobre o estilo livre de votos antigos.

### Estrutura — quatro blocos, nesta ordem

Rótulos em **CAIXA ALTA e negrito**:

```
EMENTA: [cabeçalho]
CASO EM EXAME E QUESTÃO DISCUTIDA
RAZÕES DE DECIDIR
DISPOSITIVO
```

Numeração dos parágrafos **cardinal e contínua** — do item 1 (Caso em exame) até
o dispositivo (1, 2, 3, 4, 5, 6…). **Nunca reinicia** a cada bloco.

### I. Cabeçalho (linha "EMENTA: …") — CAIXA ALTA, sem negrito no texto

Elementos, nesta sequência, separados por ponto:
1. **classe processual** — REPRESENTAÇÃO; EMBARGOS DE DECLARAÇÃO; RECURSO.
2. **perspectiva de gênero** — se o feito tramitou sob o Provimento 228/2024,
   inserir "JULGAMENTO SEGUNDO PERSPECTIVA DE GÊNERO" **logo após a classe**.
3. **preliminar/prejudicial**, se houver, já com resultado — ex.: PRELIMINAR DE
   PRESCRIÇÃO REJEITADA.
4. **verbetes do assunto** — palavras-chave da(s) conduta(s) e das normas
   violadas (ex.: DIVULGAÇÃO DE RESULTADO FAVORÁVEL. VIOLAÇÃO AO CÓDIGO DE ÉTICA
   E AO PROVIMENTO N. 205/2021).
5. **conclusão** — PROCEDÊNCIA; IMPROCEDÊNCIA; REJEIÇÃO.
6. **penalidade** — CONDENAÇÃO; SUSPENSÃO; EXCLUSÃO; PENA DE CENSURA CONVERTIDA
   EM OFÍCIO RESERVADO; SUSPENSÃO CUMULADA COM MULTA.

### II. CASO EM EXAME E QUESTÃO DISCUTIDA

- **Item 1** — objeto do procedimento em um parágrafo (para que a representação
  foi instaurada / o que se recorre).
- **Item 2** — questão a decidir: "A questão discutida consiste em saber se…".
  Havendo mais de uma: "Há duas questões a serem discutidas: a) …; b) …."
  (a preliminar entra como "a)").

### III. RAZÕES DE DECIDIR — um fundamento por item, nesta ordem

1. preliminar ou prejudicial (se houver);
2. mérito;
3. penalidade (dosimetria — circunstâncias do art. 40, conversão etc.).

### IV. DISPOSITIVO — um item

"Representação julgada procedente." / "…improcedente." / "Preliminar de
prescrição rejeitada e representação julgada procedente." / "Embargos de
declaração conhecidos e rejeitados." / "Recurso provido/desprovido."

### Modelo — sem preliminar

```
EMENTA: REPRESENTAÇÃO. [VERBETES DA CONDUTA E DAS NORMAS VIOLADAS].
PROCEDÊNCIA. [PENALIDADE].

CASO EM EXAME E QUESTÃO DISCUTIDA
1. Representação instaurada para apuração de [objeto].
2. A questão discutida consiste em saber se [conduta] configura infração ao
[dispositivo].

RAZÕES DE DECIDIR
3. [Mérito: a conduta X violou o dispositivo Y, porque…].
4. [Penalidade: circunstâncias do art. 40 / conversão / dosimetria].

DISPOSITIVO
5. Representação julgada procedente.
```

### Modelo — com preliminar de prescrição

```
EMENTA: REPRESENTAÇÃO. PRELIMINAR DE PRESCRIÇÃO REJEITADA. [VERBETES].
PROCEDÊNCIA. CONDENAÇÃO.

CASO EM EXAME E QUESTÃO DISCUTIDA
1. Representação instaurada para apuração de [objeto].
2. Há duas questões a serem discutidas: a) preliminarmente, saber se está
caracterizada a prescrição da pretensão punitiva; b) saber se [mérito].

RAZÕES DE DECIDIR
3. A preliminar de prescrição não deve ser acolhida, pois [datas e fundamento:
art. 43, §§1º e 2º, EAOAB].
4. No mérito, [fundamento].
5. [Penalidade].

DISPOSITIVO
6. Preliminar de prescrição rejeitada e representação julgada procedente.
```

### Regras de aplicação

- **Vários representados com sortes diferentes:** cabeçalho reflete os resultados
  (ex.: "…IMPROCEDÊNCIA QUANTO A DOIS REPRESENTADOS. PROCEDÊNCIA E SUSPENSÃO
  QUANTO AO TERCEIRO."); no dispositivo, **individualizar** cada um.
- **Fidelidade absoluta:** a ementa só reflete o que o voto decidiu; não antecipa
  nem extrapola.

---

## Procedimento

1. **Leia o texto do voto.** Com shell: `python3 scripts/extrair_voto.py
   <arquivo>` (.docx, .pdf, .txt, .md). Sem shell, leia o anexo direto. Vindo
   vazio, é PDF digitalizado — peça o .docx e pare.

2. **Extraia do voto**, sem inferir: classe processual; preliminares e
   prejudiciais com resultado; condutas e normas violadas (incisos do art. 34 do
   EAOAB, CED, Regulamento Geral, provimentos, súmulas); resultado por
   representado; penalidade, conversão e circunstâncias da dosimetria; incidência
   do Provimento 228/2024.

3. **Monte a ementa** aplicando o Manual pré-carregado acima — quatro blocos,
   rótulos em CAIXA ALTA e negrito, numeração cardinal contínua, ordem
   preliminar → mérito → penalidade, sem nomes das partes.

4. **Confira** que cabeçalho, RAZÕES DE DECIDIR e DISPOSITIVO dizem o mesmo
   resultado, a mesma capitulação e a mesma pena; que os incisos do art. 34 são
   os do voto; que a numeração é contínua; que cada representado aparece
   individualizado. Corrija em silêncio o que falhar.

## Entrega — cartão único, DOCX sob demanda

A entrega é **um só cartão HTML**, renderizado no chat. **Não** gere `.docx`
automaticamente: o próprio cartão exporta `.docx` no navegador quando o usuário
aperta **Exportar DOCX**. Isso mantém a saída rápida e sem ruído.

1. **Copie o template** `references/cartao-ementa.html` para um arquivo de
   trabalho.

2. **Preencha apenas o bloco de dados.** Localize, no `<script>`, o único trecho
   delimitado por `▼▼▼ DADOS DA EMENTA ▼▼▼` … `▲▲▲ FIM DOS DADOS DA EMENTA ▲▲▲`
   e substitua o objeto `const EMENTA = { … }`. **Não toque em mais nada** do
   arquivo (CSS, render, gerador de DOCX permanecem intactos). Formato:

   ```js
   const EMENTA = {
     cabecalho: "CLASSE. [PERSPECTIVA DE GÊNERO, SE INCIDIR]. [PRELIMINAR COM RESULTADO]. [VERBETES]. [CONCLUSÃO]. [PENALIDADE].",
     blocos: [
       { titulo: "Caso em exame e questão discutida",
         itens: [ { runs: [{ t: "…" }] }, { runs: [{ t: "…" }] } ] },
       { titulo: "Razões de decidir",
         itens: [ { runs: [{ t: "…" }] } ] },
       { titulo: "Dispositivo",
         itens: [ { runs: [{ t: "…" }] } ] }
     ]
   };
   ```

   - `cabecalho`: string em CAIXA ALTA, sem o rótulo "EMENTA:" (o template já o
     insere), na ordem do Manual: classe → perspectiva de gênero (se incidir) →
     preliminar com resultado → verbetes → conclusão → penalidade.
   - A numeração **cardinal contínua** (1 até o dispositivo, sem reiniciar entre
     blocos) é **gerada automaticamente pelo template** — não numere os itens
     nem inclua campo de número; apenas ordene os itens corretamente.
   - `runs`: use `{ t: "…", b: true }` para o negrito de termos-chave (ex.:
     `procedente`, `censura`, resultado e pena).
   - Sem nomes das partes. Vários representados → individualize no dispositivo.

3. **Remova a linha do "Modelo ilustrativo"** (`<p class="note" …>`) do arquivo
   preenchido — ela só serve ao template de exemplo.

4. **Publique o arquivo como artifact** (ferramenta Artifact) para renderizar o
   cartão no chat. Título "Ementa — TED OAB/SP", favicon ⚖️.

5. **Pare.** Nada além do cartão — sem introdução, sem resumo, sem `.docx`, sem
   observações finais.

**Fallback sem Artifact:** se o ambiente não dispuser da ferramenta Artifact,
entregue o **texto da ementa** (quatro blocos, numeração contínua) direto no
chat e, havendo shell, também o `.docx` — sem o botão Exportar do cartão, o
arquivo volta a ser entregue junto. Gere-o gravando a ementa num `.md` com os
**rótulos entre `**`** (é o que vira negrito) e cada item numerado em linha
própria, e rodando `python3 scripts/gerar_docx.py <ementa.md>`.
