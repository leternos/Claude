# DJEN OAB/SP na AWS Lambda (serverless, grátis)

Port serverless do projeto: uma função **AWS Lambda** rodando na região
**`sa-east-1` (São Paulo)** — para que a chamada à API do CNJ saia por IP
brasileiro — disparada todo dia às **5:59 (horário de Brasília)** por um
**EventBridge Scheduler**. Sem servidor para manter, sem depender de nenhuma
máquina ligada.

`lambda_handler.py` reaproveita `../djen.py` e `../notificacao.py` sem
alterações — ambos usam só a biblioteca padrão do Python, então o pacote de
deploy não tem nenhuma dependência para instalar.

## Custo: R$ 0

No seu volume de uso (1 disparo por dia, ~30/mês):

| Serviço | Camada "Always Free" (permanente) | Seu uso |
| --- | --- | --- |
| AWS Lambda | 1.000.000 requisições/mês | ~30/mês |
| EventBridge Scheduler | 14.000.000 invocações/mês | ~30/mês |

Ambas as camadas grátis **valem também em `sa-east-1`** e não expiram — não é
um teste de 12 meses. A AWS pede um cartão de crédito para verificar a conta,
mas isso não gera cobrança dentro do Always Free.

## Pré-requisitos

1. Uma conta AWS (crie em <https://aws.amazon.com> se ainda não tiver).
2. **AWS CLI v2** instalado e autenticado: `aws configure` (peça ao
   administrador da conta, ou crie um usuário IAM próprio, com permissão para
   criar funções Lambda, roles do IAM e schedules do EventBridge Scheduler).
3. `zip` e `python3` disponíveis no terminal (já usados pelo resto do projeto).

## Passo a passo

1. **Confira `config.env`** — já vem preenchido com sua OAB, nome e e-mail;
   ajuste se precisar.

2. **Informe as credenciais de e-mail/WhatsApp.** O script reaproveita a
   mesma convenção do projeto local: variável de ambiente **ou** arquivo na
   pasta `djen-oab-sp/` (um nível acima desta pasta):

   ```bash
   echo 'SG.suaApiKey' > ../.sendgrid_key        # SendGrid (provedor padrão)
   # ou, para SMTP:  echo 'senha-de-app' > ../.smtp_senha
   # se for usar WhatsApp: ../.twilio_sid e ../.twilio_token
   ```

3. **Publique:**
   ```bash
   ./deploy.sh
   ```
   Cria a role de execução da Lambda, empacota o código, publica a função em
   `sa-east-1` e cria o agendamento das 5:59. É idempotente — rode de novo
   sempre que mudar `config.env`, `djen.py` ou `notificacao.py`.

4. **Teste sem esperar as 5:59:**
   ```bash
   ./invocar_teste.sh                # hoje
   ./invocar_teste.sh 2026-07-19     # uma data específica
   ```
   Mostra o retorno da função e os logs recentes do CloudWatch.

5. **Acompanhe os logs quando quiser:**
   ```bash
   aws logs tail /aws/lambda/djen-oab-sp-diario --region sa-east-1 --since 1h
   ```

6. **Para desfazer tudo** (função, roles, agendamento):
   ```bash
   ./destroy.sh
   ```

## O que muda em relação ao app local

- Sem `config.json`/arquivos de segredo dentro do pacote — tudo vem de
  variáveis de ambiente da própria função Lambda (definidas pelo `deploy.sh`
  a partir de `config.env` + dos arquivos de segredo).
- Sem `exports/` persistente — o `/tmp` da Lambda é apagado a cada execução;
  o CSV/HTML são gerados só para anexar ao e-mail, não ficam guardados. Se
  quiser um histórico, dá para adicionar um bucket S3 depois — não é
  necessário para o envio diário funcionar.
- `verificar.py`/`relatorio.py`/`app.py` continuam existindo e funcionando
  normalmente para uso local/manual — este diretório só substitui o
  agendamento (`agendamento/instalar_cron.sh`) por uma versão que não depende
  de nenhuma máquina seu ligada.
