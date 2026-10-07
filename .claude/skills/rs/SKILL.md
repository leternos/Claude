---
name: rs
description: >-
  Orça uma lista de compras no Pão de Açúcar e no Santa Luzia (São Paulo) com
  os preços do dia nos sites das duas lojas e devolve uma tabela comparativa
  item a item, com o total de cada loja e onde a lista sai mais barata. Use
  quando o usuário digitar /rs, colar uma lista de compras e perguntar "quanto
  fica", "valor dessa lista", "orçamento do mercado", ou citar Pão de Açúcar ou
  Santa Luzia junto com preços. Interaja sempre em português.
---

# /rs — orçamento de lista no Pão de Açúcar e no Santa Luzia

Entra uma lista de compras, sai **quanto ela custa hoje em cada loja**, item a
item, com os dois totais lado a lado. **Sempre em português**, valores em
`R$ 0,00`.

## Princípio central

**Preço real primeiro, estimativa só como último recurso e sempre rotulada.**
Nunca apresente um valor estimado como se tivesse vindo do site. Cada preço da
tabela tem uma origem e essa origem aparece na resposta.

## 1. Ler a lista

- A lista vem como argumento (`/rs 2 doritos, 1 pack de coca 600ml…`) ou na
  mensagem. Sem lista, peça: "Cole a lista de compras."
- Normalize cada linha em **quantidade + unidade + produto + especificação**:
  - `2 doritos sabor tradicional` → 2 un · Doritos Queijo Nacho (tradicional)
  - `5 kilos de tangerina` → 5 kg · tangerina (preço por kg)
  - `3 bandejas de peito de frango sem pele e sem osso` → 3 bandejas · filé de
    peito de frango
  - `1 pack de coca zero 600ml` → 1 pack · Coca-Cola Zero 600ml
- Corrija grafia sem comentar (`amendoin` → amendoim, `sheetos` → Cheetos,
  `bandeija` → bandeja).
- **Não pergunte nada antes de buscar.** Ambiguidades (tamanho do pacote,
  quantas garrafas tem o pack, peso da bandeja) se resolvem com a regra da
  seção 3 e viram premissa declarada no fim.

## 2. Buscar os preços — nesta ordem

Tente cada via até uma funcionar; use a mesma via para as duas lojas sempre
que possível. Busque os itens em paralelo quando a ferramenta permitir.

| Loja | Site | Busca |
|---|---|---|
| Pão de Açúcar | `https://www.paodeacucar.com` | `https://www.paodeacucar.com/busca?terms=<termo>` |
| Santa Luzia | `https://www.santaluzia.com.br` | use a caixa de busca do site |

1. **Navegador** — se houver ferramentas de navegador disponíveis (Claude in
   Chrome `mcp__claude-in-chrome__*` ou o navegador embutido
   `mcp__Claude_Browser__*`), carregue a skill correspondente
   (`chrome-browser` ou `built-in-browser`) e use-o. É a via mais confiável:
   os dois sites renderizam preço via JavaScript e o Pão de Açúcar pede CEP ou
   loja — se pedir, use o CEP que o usuário informou ou pergunte uma vez e
   reaproveite.
2. **WebFetch** na URL de busca de cada produto.
3. **API do Pão de Açúcar** via `curl` (plataforma GPA):
   `https://api.vendas.gpa.digital/pa/search/search?terms=<termo>&page=1&itemsPerPage=12`
   — se a rota tiver mudado, não insista: siga para a próxima via.
4. **WebSearch** restrito ao domínio (`allowed_domains: ["paodeacucar.com"]`
   ou `["santaluzia.com.br"]`) para achar a página do produto e então
   WebFetch nela.

Se o ambiente bloquear os domínios (erro `EGRESS_BLOCKED`, `403` no proxy,
`CONNECT tunnel failed`), diga em uma linha qual host foi bloqueado e que ele
pode ser liberado nas configurações de rede do ambiente — e continue com o que
der (seção 4).

## 3. Escolher o produto certo em cada loja

- Prefira a **marca e o sabor pedidos**; "qualquer sabor" → o mais barato da
  marca.
- Tamanho não especificado → a **embalagem padrão/mais vendida** (ex.: Doritos
  ~140 g, Cheetos ~115 g). Use o **mesmo tamanho nas duas lojas** para a
  comparação ser justa; se uma loja não tiver, pegue o mais próximo e anote.
- **Pack** de refrigerante sem quantidade → pack de 6 unidades se a loja
  vender; se só houver unidade avulsa, calcule unidade × 6 e anote.
- **Por kg** (frutas, carnes): preço/kg × quantidade. Bandeja sem peso → use o
  peso da bandeja anunciada no site, ou 1 kg, e anote.
- **Oferta**: registre o preço de oferta quando o site mostrar, e o preço cheio
  entre parênteses. Ofertas que exigem cadastro (Clube Extra / Pão de Açúcar
  Mais) → anote "(clube)".
- Item não encontrado numa loja → `não encontrado` na célula; não invente.

## 4. Quando não der para ler o site

Se uma loja (ou as duas) estiver inacessível por todas as vias:

- Diga isso **logo no início** da resposta, sem rodeio.
- Ofereça uma **estimativa** só se ajudar, com a coluna marcada `estimado`,
  baseada em preço típico de varejo premium em São Paulo — e uma **faixa** no
  total (ex.: R$ 420 a R$ 510), nunca um número seco.
- Santa Luzia costuma ser mais caro que o Pão de Açúcar em itens de marca; não
  use isso para "preencher" preço — só como ressalva na estimativa.

## 5. Calcular

Faça as contas com código (`python3 -c …`), não de cabeça: subtotal por item =
preço × quantidade, total por loja, diferença em R$ e em %. Arredonde só na
exibição.

## 6. Formato da resposta

Curta, direta, nesta ordem:

```
**Pão de Açúcar: R$ 000,00 · Santa Luzia: R$ 000,00**
A lista sai R$ 00,00 (00%) mais barata no <loja>.

| Item | Qtd | Pão de Açúcar | Santa Luzia |
|---|---|---|---|
| Doritos Queijo Nacho 140 g | 2 | 29,98 (14,99) | 33,98 (16,99) |
| … | | | |
| **Total** | | **000,00** | **000,00** |

Premissas: pack = 6 garrafas; bandeja de frango ≈ 1 kg; …
Fonte: preços lidos em paodeacucar.com e santaluzia.com.br em <data>.
```

- Células: subtotal e, entre parênteses, o preço unitário (ou R$/kg).
- Marque `*` nos preços de oferta e explique numa linha abaixo da tabela.
- Se um item faltar numa loja, o total daquela loja leva a nota "sem <item>".
- Se valer a pena, uma linha final: "Dividindo a compra (cada item na loja
  mais barata): R$ 000,00."
- Nada de texto extra além disso — o usuário quer o número.
