---
name: ementario
description: >-
  Gera a EMENTA de um voto no padrão do Manual de Padronização de Ementas do TED
  OAB/SP. DISPARE AUTOMATICAMENTE, sem que o usuário peça, sempre que ele
  anexar, enviar ou apontar um arquivo .docx, .pdf ou .txt cujo nome contenha
  "voto" — inclusive quando a mensagem vier só com o caminho do arquivo, sem
  texto nenhum. Entrega a ementa no chat e um .docx, e mais nada.
---

# Gerador de ementas — padrão TED OAB/SP

Entra um voto, sai a ementa. A skill **não interpreta o voto, não julga, não
revisa, não comenta**. Ela lê o que o voto decidiu e escreve isso no formato do
Manual.

## Escopo — o que NÃO fazer

- Não analisar o mérito, não avaliar a prova, não conferir a dosimetria.
- Não apontar contradições, erros, lacunas ou sugestões de melhoria do voto.
- Não resumir o voto, não explicar a ementa, não comentar o que foi feito.
- Não acrescentar fundamento, precedente, norma ou verbete que o voto não traga.
- Não perguntar nada antes de gerar. Havendo dúvida sobre um elemento, escreva
  `[VERIFICAR]` no lugar e siga.

## Procedimento

1. **Leia o texto do voto.** Se o ambiente tiver shell:
   `python3 scripts/extrair_voto.py <arquivo>` (aceita .docx, .pdf, .txt). Se não
   tiver, leia o arquivo anexado diretamente. Vindo vazio, é PDF digitalizado —
   peça o .docx e pare.

2. **Leia `references/manual-ementa-ted.md`** por inteiro, a cada execução.

3. **Extraia do voto**, sem inferir: classe processual; preliminares e
   prejudiciais com o respectivo resultado; condutas e normas violadas (incisos
   do art. 34 do EAOAB, CED, Regulamento Geral, provimentos, súmulas); resultado
   por representado; penalidade, conversão e as circunstâncias que o voto usou
   na dosimetria; incidência do Provimento 228/2024.

4. **Monte a ementa** nos quatro blocos do Manual — cabeçalho, CASO EM EXAME E
   QUESTÃO DISCUTIDA, RAZÕES DE DECIDIR, DISPOSITIVO —, rótulos em CAIXA ALTA e
   negrito, numeração cardinal contínua do item 1 ao dispositivo, ordem
   preliminar → mérito → penalidade. Sem nomes das partes.

5. **Confira** que cabeçalho, RAZÕES DE DECIDIR e DISPOSITIVO dizem o mesmo
   resultado, a mesma capitulação e a mesma pena; que os incisos do art. 34 são
   os do voto; que a numeração é contínua; que cada representado aparece
   individualizado. Corrija em silêncio o que falhar.

## Entrega

Exatamente duas coisas, nesta ordem:

1. o texto da ementa no chat, pronto para copiar;
2. o `.docx`, gerado com
   `python3 scripts/gerar_docx.py <ementa.md>` quando houver shell.

Nenhuma linha além disso — sem introdução, sem resumo, sem observações finais.
