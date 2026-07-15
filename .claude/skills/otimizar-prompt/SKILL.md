---
name: otimizar-prompt
description: >-
  Otimiza prompts para Claude e outros LLMs. Lê o prompt em rascunho do usuário,
  faz perguntas de esclarecimento apenas quando há ambiguidade ou informação
  faltando, e reescreve o prompt aplicando boas práticas de prompt engineering
  (clareza, contexto, exemplos, estrutura com tags, formato de saída e critérios
  de sucesso). Use quando o usuário pedir para melhorar, otimizar, refinar,
  reescrever ou "deixar melhor" um prompt, ou quando ele colar um rascunho de
  prompt e quiser a versão final. Interaja sempre em português.
---

# Otimizar Prompt

Transforma um prompt em rascunho na melhor versão possível para uso com Claude e
outros LLMs. **Sempre interaja em português.**

## Princípio central

Otimizar é **amplificar a intenção do usuário, não substituí-la**. Você deixa o
prompt mais claro, estruturado e completo — mas não inventa requisitos que o
usuário não pediu nem muda o objetivo dele. Na dúvida sobre o que ele quer,
**pergunte** (etapa 2); nunca preencha lacunas importantes com suposições
silenciosas.

## Fluxo de trabalho

### 1. Receber o rascunho

- Se o usuário já forneceu o prompt (como argumento da skill ou na mensagem),
  use-o.
- Se não forneceu, peça: *"Cole aqui o prompt que você quer otimizar."*

### 2. Diagnosticar

Leia o rascunho e avalie cada dimensão abaixo. Marque o que está **claro**,
**ausente** ou **ambíguo**:

| Dimensão | Pergunta-chave |
|---|---|
| **Objetivo** | Qual é a tarefa concreta? O resultado esperado está claro? |
| **Contexto** | Há informação de fundo suficiente para o modelo executar bem? |
| **Papel / público** | Quem o modelo deve "ser"? Para quem é a resposta? |
| **Formato de saída** | Texto corrido, lista, JSON, tabela, tamanho, tom? |
| **Restrições** | O que evitar, limites de tamanho, tom, idioma, escopo? |
| **Exemplos** | Um ou dois exemplos de entrada→saída ajudariam a fixar o padrão? |
| **Dados variáveis** | Onde entram os dados que mudam a cada uso (se for um template)? |
| **Critério de sucesso** | Como saber se a resposta ficou boa? |

### 3. Perguntar — só o que for essencial

Faça perguntas **apenas** sobre lacunas que mudam de verdade o prompt final.
Não pergunte o que dá para inferir com segurança ou resolver com um padrão
razoável.

- Use a ferramenta **AskUserQuestion** quando estiver no Claude Code, agrupando
  de **1 a 4 perguntas** numa única rodada (nunca uma de cada vez).
- Ofereça opções concretas quando possível (ex.: formato de saída → *lista /
  parágrafo / JSON / tabela*), sempre deixando espaço para resposta livre.
- Se o rascunho já estiver claro o suficiente, **pule esta etapa** e vá direto
  para a reescrita, declarando as suposições que fez.

Bons gatilhos para perguntar: objetivo ambíguo, público/tom indefinido quando
importam, formato de saída não especificado numa tarefa que claramente precisa
de um, ou falta de um dado essencial que só o usuário tem.

### 4. Reescrever

Aplique as **técnicas de otimização** (abaixo) na medida certa para a tarefa.
Nem todo prompt precisa de todas elas — um pedido simples fica melhor curto.
Calibre a complexidade ao tamanho do problema.

### 5. Apresentar

Entregue nesta ordem:

1. **✨ Prompt otimizado** — dentro de um bloco de código (```), pronto para
   copiar e colar. Nada de comentários dentro do bloco.
2. **🔧 O que mudou e por quê** — 3 a 6 bullets curtos explicando as melhorias
   principais (ex.: "adicionei um papel de especialista", "estruturei com tags
   XML", "especifiquei saída em JSON").
3. **📌 Suposições** — se você preencheu alguma lacuna sozinho, liste aqui para
   o usuário confirmar ou corrigir.
4. **💡 Opcional** — sugestões de próximo nível que fugiriam do pedido original
   (ex.: "se for repetir muito, vale virar um template com variáveis").

## Técnicas de otimização

Aplique conforme a necessidade da tarefa:

1. **Seja claro e direto.** Instruções explícitas, na ordem de execução.
   Prefira dizer o que fazer em vez do que não fazer. Numere passos sequenciais.

2. **Dê contexto.** Explique o propósito, o público e como a saída será usada —
   o modelo responde melhor quando entende o "porquê".

3. **Atribua um papel.** Comece com uma persona/expertise ("Você é um revisor
   técnico sênior especializado em...") para calibrar tom e profundidade.

4. **Estruture com tags XML.** Separe partes distintas com tags como
   `<contexto>`, `<instrucoes>`, `<exemplos>`, `<dados>`, `<formato>`. Isso
   evita que o modelo confunda instruções com conteúdo.

5. **Use exemplos (multishot).** Para tarefas com padrão de saída, inclua 1–3
   exemplos de entrada→saída, diversos e representativos. Exemplos valem mais
   que descrições longas.

6. **Dê espaço para pensar (chain of thought).** Em tarefas de raciocínio,
   peça "pense passo a passo antes de responder" ou reserve uma seção de
   rascunho (`<raciocinio>`) antes da resposta final.

7. **Especifique o formato de saída.** Diga exatamente a estrutura esperada
   (JSON com tais campos, tabela com tais colunas, no máximo N palavras). Se for
   JSON, mostre o schema.

8. **Defina critérios de sucesso e casos extremos.** Diga o que fazer quando
   faltar informação, quando a entrada for inválida, ou o que caracteriza uma
   boa resposta.

9. **Quebre tarefas complexas.** Se o pedido faz coisas demais de uma vez,
   sugira encadear em etapas ou dividir em prompts menores.

10. **Prefill / âncora de saída.** Quando útil, indique como a resposta deve
    começar para forçar o formato (ex.: começar direto com `{` para JSON).

## Checklist antes de entregar

- [ ] O objetivo do prompt original foi **preservado** (nada de escopo inflado).
- [ ] Um estranho leria o prompt otimizado e saberia exatamente o que fazer.
- [ ] O formato de saída está definido (quando a tarefa pede).
- [ ] As técnicas usadas são proporcionais à complexidade — sem enfeite inútil.
- [ ] Suposições preenchidas estão declaradas.
- [ ] O prompt final está em um bloco de código, pronto para copiar.

## Exemplo (antes → depois)

**Rascunho do usuário:**
> "escreva sobre marketing digital"

**Diagnóstico:** objetivo vago (que tipo de texto?), público e formato ausentes,
sem tamanho nem tom. Vale perguntar 2–3 coisas antes de reescrever.

**Após esclarecer** (público = donos de pequenos negócios; formato = post de
blog; objetivo = gerar leads):

```
Você é um estrategista de marketing digital escrevendo para donos de
pequenos negócios sem experiência técnica.

Escreva um post de blog sobre marketing digital com estas características:
- Objetivo: convencer o leitor a começar com um primeiro passo prático hoje.
- Público: dono de pequeno negócio, linguagem simples, sem jargão.
- Tom: encorajador e direto ao ponto.
- Tamanho: 500–700 palavras.

Estrutura:
1. Um título chamativo.
2. Uma abertura que fale de uma dor real do pequeno empreendedor.
3. Três táticas acionáveis, cada uma com um exemplo concreto.
4. Um encerramento com uma chamada para ação clara.
```

**O que mudou:** papel definido, público e tom explícitos, objetivo mensurável,
tamanho limitado e estrutura em passos — de uma frase ambígua para um briefing
que o modelo executa com precisão.
