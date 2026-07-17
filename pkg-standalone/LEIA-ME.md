# Familia Romana — Comandos curtos (iPhone + Mac)

Zero dependências: só Python 3 (stdlib). Sem pip, sem servidor, sem internet.

## Mac — instalação (uma vez)
```bash
cd <pasta-extraída>
./instalar-mac.sh
```
Depois, em qualquer terminal:
```
decl puella
conj ponere
trad villa
cor "Iulia puella Romana est"
fr sig rosa        # forma genérica: fr <comando> <arg>
```

## iPhone (a-Shell, grátis)
1. Copie a pasta para o a-Shell via app Files
2. Dentro do a-Shell: `cd` até a pasta e `sh instalar-iphone-ashell.sh`
3. Feche e reabra o a-Shell → `conj ponere` direto
   (se o alias não carregar, rode `source ~/Documents/.profile`)

Pyto/Pythonista: sem shell de aliases — use o modo interativo:
rode o .py sem argumentos e digite `conj ponere` no prompt `>`.

## Como funciona o comando curto
O script reconhece o nome pelo qual foi invocado (symlink/alias
`decl`, `conj`, `trad`, `sig`, `cor`) e o usa como comando — estilo busybox.

## Arquivos
- familia_romana_standalone.py — tudo em um (o .db ao lado é opcional:
  sem ele, só os exemplos do livro em `trad` e a checagem do `cor` degradam)
- familia_romana.db — 7.566 formas do livro
