# Rodar o DJEN OAB/SP no Claude Cowork (máquina local, no Brasil)

Este guia é para executar o projeto **na sua própria máquina** através do Claude
Cowork. Como a busca sai pelo **seu IP brasileiro**, você vê as **publicações
reais** (a API do CNJ bloqueia acessos de fora do Brasil).

> Regra de ouro: o que decide o acesso é o **IP de quem faz a requisição**. No
> Cowork com execução local, quem roda o código é a sua máquina → IP do Brasil → OK.
> Se o Cowork rodar na nuvem, cai no mesmo bloqueio 403 (aí use `DJEN_PROXY`).

## Passo a passo

1. **Abra o projeto no Cowork** apontando para esta pasta (`djen-oab-sp/`),
   a partir da branch `claude/djen-oab-sp-webapp-n0wp6z` do repositório.

2. **Confira a configuração** em `config.json` (já vem preenchida):
   - `numeroOab`: `124536`, `ufOab`: `SP`
   - `nomeAdvogado`: `Antonio Carlos Monteiro da Silva Filho`
   - `email.provedor`: `sendgrid`, `email.para`: `gcforte@me.com`

3. **Informe a credencial do e-mail** (SendGrid). Peça ao Claude no Cowork, ou rode:
   ```bash
   echo 'SG.suaApiKey' > .sendgrid_key && chmod 600 .sendgrid_key
   ```
   (Como obter: conta no SendGrid → verificar `gcforte@me.com` como *Single
   Sender* → API Keys → permissão *Mail Send*.)

4. **Verifique se está tudo pronto:**
   ```bash
   python3 verificar.py
   ```
   O ideal é ver `[OK]` na linha "Conexão com o DJEN OK". Se aparecer
   "Bloqueio geográfico", o Cowork está executando fora do Brasil.

5. **Gere o relatório real do dia** (abre o HTML no navegador):
   ```bash
   python3 relatorio.py
   ```
   Ou peça no chat do Cowork: *"rode o relatório de hoje"* — o Claude executa e
   te mostra o HTML preenchido com as suas publicações.

6. **Dispare o e-mail (e WhatsApp, se ligado) na hora, para testar:**
   ```bash
   python3 daily_export.py
   ```

## Agendar as 5:59 na sua máquina

Com o projeto rodando localmente, o agendamento também roda aí (a máquina precisa
estar ligada às 5:59):

```bash
./agendamento/instalar_cron.sh      # Linux/macOS
```
No macOS, para sobreviver a reinícios, use o modelo em
`agendamento/com.djen-oabsp.daily.plist` (veja o README). No Windows, o comando
`schtasks` está no README.

## Se o Cowork rodar na nuvem (não na sua máquina)

Aí o IP não é brasileiro. Duas saídas:
- Aponte `DJEN_PROXY` para um proxy/VPS no Brasil que você controle:
  ```bash
  export DJEN_PROXY="http://usuario:senha@meu-proxy-br:8080"
  ```
- Ou rode o projeto no app de **desktop do Cowork**, com execução local.

Rode `python3 verificar.py` sempre que tiver dúvida — ele diz na hora se o IP
atual enxerga o DJEN.
