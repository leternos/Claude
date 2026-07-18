# DJEN OAB/SP — consulta e exportação diária

Webapp que pesquisa no **DJEN** (Diário de Justiça Eletrônico Nacional, do CNJ) as
publicações vinculadas a um número de OAB (padrão UF **SP**), permite exportar os
resultados e roda **todo dia às 5:59** enviando um e-mail com as publicações do dia
para `gcforte@me.com`.

Fonte de dados: API pública oficial `https://comunicaapi.pje.jus.br/api/v1/comunicacao`.

> **Importante — rode no Brasil:** o CDN do CNJ **bloqueia IPs de fora do Brasil**
> (HTTP 403). Execute o app e o agendamento em uma máquina/rede com IP brasileiro
> (seu computador, ou um servidor/VPS em região brasileira). Foi por isso que o
> agendamento não pôde ficar no ambiente de nuvem do Claude (IP nos EUA).

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

2. Crie a senha do SMTP. O padrão do `config.json` é o iCloud (`smtp.mail.me.com`),
   já que o destino é `gcforte@me.com` — gere uma **senha de app** em
   <https://account.apple.com> → Segurança → Senhas de app. Depois:

   ```bash
   # opção A: variável de ambiente
   export DJEN_SMTP_SENHA='sua-senha-de-app'
   # opção B: arquivo (útil para cron/launchd)
   echo 'sua-senha-de-app' > djen-oab-sp/.smtp_senha && chmod 600 djen-oab-sp/.smtp_senha
   ```

   Para usar Gmail ou outro provedor, ajuste `smtp_host`, `smtp_porta`,
   `smtp_usuario` e `de` no bloco `email` do `config.json`.

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
| `app.py` | Webapp (servidor local, porta 8859) |
| `djen.py` | Cliente da API do DJEN + geradores CSV/HTML/JSON/resumo |
| `daily_export.py` | Rotina diária: busca do dia, exporta e envia e-mail |
| `config.json` | OAB monitorada e configuração de e-mail |
| `agendamento/` | Instalador de cron e modelo de launchd (5:59) |
| `tests/` | API simulada + testes de ponta a ponta |
