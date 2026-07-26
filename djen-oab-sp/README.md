# DJEN OAB/SP — consulta e exportação diária

Webapp que pesquisa no **DJEN** (Diário de Justiça Eletrônico Nacional, do CNJ) as
publicações vinculadas a um número de OAB (padrão UF **SP**), permite exportar os
resultados e roda **todo dia às 5:59** enviando um e-mail com as publicações do dia
para `gcforte@me.com`.

Fonte de dados: API pública oficial `https://comunicaapi.pje.jus.br/api/v1/comunicacao`.

> **Importante — precisa de IP no Brasil:** o CDN do CNJ **bloqueia IPs de fora do
> Brasil** (HTTP 403). Execute o app e o agendamento em uma máquina/rede com IP
> brasileiro (seu computador, ou um servidor/VPS em região brasileira). Se precisar
> rodar de fora do país (ex.: buscar inline no chat), use um **proxy no Brasil**
> apontando `DJEN_PROXY` (veja abaixo).

### Rodar de fora do Brasil via proxy (`DJEN_PROXY`)

Para que a busca funcione a partir de um ambiente fora do país, aponte para um
proxy/VPS brasileiro que você controle:

```bash
export DJEN_PROXY="http://usuario:senha@meu-proxy-br:8080"
python3 relatorio.py        # a requisição ao CNJ sai pelo IP do proxy
```

Sem `DJEN_PROXY`, as requisições saem pelo IP local da máquina.

Sem dependências externas: só Python 3.9+ (biblioteca padrão).

## 1. Webapp (consulta manual)

```bash
cd djen-oab-sp
python3 app.py            # abre em http://localhost:8859
```

Na interface: informe o número da OAB, a UF (SP por padrão) e o período (o dia de
hoje já vem preenchido, no horário de Brasília). Botões **Exportar CSV/HTML/JSON**
baixam o resultado; **Salvar como padrão** grava a OAB no `config.json` para a
exportação diária usar.

## 2. Exportação diária + e-mail

1. Configure sua OAB no `config.json` (ou pela interface, botão *Salvar como padrão*):

   ```json
   { "numeroOab": "123456", "ufOab": "SP", ... }
   ```

2. Escolha o provedor de e-mail em `config.json` → `email.provedor`:

   **a) `"smtp"` (padrão)** — iCloud (`smtp.mail.me.com`), já que o destino é
   `gcforte@me.com`. Gere uma **senha de app** em <https://account.apple.com> →
   Segurança → Senhas de app. Depois:

   ```bash
   export DJEN_SMTP_SENHA='sua-senha-de-app'                    # ou:
   echo 'sua-senha-de-app' > djen-oab-sp/.smtp_senha && chmod 600 djen-oab-sp/.smtp_senha
   ```

   Para Gmail/outro, ajuste `smtp_host`, `smtp_porta`, `smtp_usuario` e `de`.

   **b) `"sendgrid"` (Twilio SendGrid)** — API HTTP, sem senha de app, 100 e-mails/dia
   grátis. Passos: crie a conta, **verifique o remetente** (Settings → Sender
   Authentication → *Single Sender* com `gcforte@me.com`), gere uma **API key**
   (Settings → API Keys, permissão *Mail Send*) e defina `email.provedor` como
   `"sendgrid"`. Depois:

   ```bash
   export SENDGRID_API_KEY='SG.sua-api-key'                     # ou:
   echo 'SG.sua-api-key' > djen-oab-sp/.sendgrid_key && chmod 600 djen-oab-sp/.sendgrid_key
   ```

   > O e-mail vai com o **relatório HTML no corpo** (além dos anexos CSV e HTML),
   > nos dois provedores.

3. *(Opcional)* **Alerta por WhatsApp (Twilio).** Além do e-mail, dá para receber
   uma mensagem curta no WhatsApp ("N publicações hoje"). Configure o bloco
   `whatsapp` do `config.json` (`"habilitado": true`, seu número em `"para"` no
   formato `"whatsapp:+55DDDNÚMERO"`), e informe as credenciais do Twilio:

   ```bash
   export TWILIO_ACCOUNT_SID='ACxxxxxxxx'
   export TWILIO_AUTH_TOKEN='seu-token'          # ou arquivos .twilio_sid / .twilio_token
   ```

   Para testar rápido, use o **Sandbox de WhatsApp** do Twilio (Console → Messaging →
   Try it out → WhatsApp): mantenha `"de": "whatsapp:+14155238886"` e envie a
   frase de adesão (`join <palavra>`) do seu celular para o número do sandbox.
   Para produção (mensagem enviada 5:59, fora da janela de 24 h), é preciso um
   **remetente WhatsApp aprovado** e um **template** aprovado no Twilio — o e-mail
   continua sendo o canal principal; o WhatsApp é só o aviso.

3. Teste manualmente:

   ```bash
   python3 daily_export.py --sem-email      # só gera exports/
   python3 daily_export.py                  # gera e envia o e-mail
   python3 daily_export.py --data 2026-07-17
   ```

   Os arquivos ficam em `exports/djen_OAB-<numero>-SP_<data>.{csv,html,json}` e o
   e-mail leva o resumo no corpo com CSV e HTML anexos. Em dia sem publicação
   (fim de semana/feriado) o e-mail avisa que não houve nada — desative isso com
   `"enviar_quando_vazio": false`.

## 3. Agendar às 5:59

- **Linux/macOS (cron):** `./agendamento/instalar_cron.sh` — instala
  `59 5 * * *` no seu crontab (horário local da máquina).
- **macOS (launchd, sobrevive melhor a reinícios):** edite os caminhos em
  `agendamento/com.djen-oabsp.daily.plist`, copie para `~/Library/LaunchAgents/`
  e rode `launchctl load ~/Library/LaunchAgents/com.djen-oabsp.daily.plist`.
- **Windows (Agendador de Tarefas):**

  ```bat
  schtasks /Create /SC DAILY /ST 05:59 /TN "DJEN OAB SP" ^
    /TR "cmd /c cd /d C:\caminho\djen-oab-sp && python daily_export.py >> exports\daily.log 2>&1"
  ```

## 4. Testes

```bash
cd djen-oab-sp
python3 tests/run_tests.py
```

Os testes sobem uma API simulada do DJEN (`tests/mock_api.py`) e exercitam a
busca com paginação, os três formatos de exportação, o `daily_export.py` e os
endpoints do webapp — sem depender da rede.

## Estrutura

| Arquivo | Função |
| --- | --- |
| `app.py` | Painel local (porta 8859), sem formulário, OAB fixa do config |
| `relatorio.py` | Gera o relatório HTML do dia (sem argumentos) e abre no navegador |
| `verificar.py` | Autoteste do ambiente (config, credenciais, acesso ao DJEN) |
| `COWORK.md` | Guia para rodar no Claude Cowork local (com dados reais) |
| `djen.py` | Cliente da API do DJEN (com suporte a `DJEN_PROXY`) + geradores |
| `daily_export.py` | Rotina diária: busca do dia, exporta e envia e-mail |
| `notificacao.py` | Notificações: e-mail (SMTP/SendGrid) e WhatsApp (Twilio) |
| `config.json` | OAB monitorada e configuração de e-mail/provedor |
| `agendamento/` | Instalador de cron e modelo de launchd (5:59) |
| `tests/` | API simulada + testes de ponta a ponta |
