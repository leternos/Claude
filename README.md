# Skills do Claude Code

Repositório de skills personalizadas para o [Claude Code](https://code.claude.com/docs)
e pequenos aplicativos.

## `/diff` — Comparador de Arquivos

Aplicação [FastAPI](diff/) com interface HTML para comparar dois arquivos —
texto ou Word (`.docx` e `.doc`) — com marcação no estilo "Controlar
Alterações" do Word: vermelho tachado
para o que saiu, verde sublinhado para o que entrou e destaque amarelo (com
diff palavra a palavra) nas linhas alteradas. Inclui visão unificada
("Documento marcado") e visão lado a lado. Veja o [README do app](diff/README.md).

Há também uma **versão estática exportada** em
[`diff/comparador.html`](diff/comparador.html): o app inteiro num único
arquivo HTML que roda 100% no navegador, sem servidor.

```bash
cd diff
pip install -r requirements.txt
uvicorn main:app --reload
```

## `/otimizar-prompt`

Skill que **lê um prompt em rascunho, tira dúvidas quando necessário e reescreve
o prompt para o melhor uso e otimização possível** — aplicando boas práticas de
prompt engineering para Claude e outros LLMs. Toda a interação é em português.

### Como usar

No Claude Code, dentro deste repositório:

```
/otimizar-prompt escreva um email de cobrança para um cliente atrasado
```

Ou invoque sem argumento e cole o rascunho quando solicitado:

```
/otimizar-prompt
```

### O que a skill faz

1. **Lê** o seu rascunho de prompt.
2. **Diagnostica** o que está claro, ausente ou ambíguo (objetivo, contexto,
   público, formato de saída, restrições, exemplos, critério de sucesso).
3. **Pergunta** — só o que for essencial e que mude de verdade o resultado,
   agrupando as perguntas numa única rodada.
4. **Reescreve** aplicando as técnicas certas para a tarefa (papel, contexto,
   tags XML, exemplos, formato de saída, raciocínio passo a passo).
5. **Apresenta** o prompt otimizado pronto para copiar, mais um resumo do que
   mudou e as suposições feitas.

O detalhamento completo do comportamento fica em
[`.claude/skills/otimizar-prompt/SKILL.md`](.claude/skills/otimizar-prompt/SKILL.md).

## `/rs`

Orça uma lista de compras no **Pão de Açúcar** e no **Santa Luzia** com os
preços do dia nos sites das duas lojas e devolve uma tabela comparativa item a
item, com o total de cada loja.

```
/rs 2 doritos, 1 pack de coca zero 600ml, 5 kg de tangerina
```

Ler os sites exige acesso de rede a `paodeacucar.com` e `santaluzia.com.br`
(ou um navegador conectado). Sem isso, a skill avisa e entrega só uma
estimativa rotulada como tal.

## Estrutura

```
.claude/
└── skills/
    ├── otimizar-prompt/
    │   └── SKILL.md
    └── rs/
        └── SKILL.md
```

Para adicionar novas skills, crie uma pasta em `.claude/skills/<nome-da-skill>/`
com um arquivo `SKILL.md` contendo o frontmatter (`name`, `description`) e as
instruções.
