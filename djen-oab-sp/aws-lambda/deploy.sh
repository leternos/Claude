#!/usr/bin/env bash
# Publica a função Lambda do DJEN OAB/SP e agenda o EventBridge Scheduler
# para disparar todo dia às 5:59 (horário de Brasília), com a função rodando
# em sa-east-1 (São Paulo) para que a chamada à API do CNJ saia por IP
# brasileiro. Idempotente: pode rodar de novo após editar config.env ou o
# código em ../djen.py / ../notificacao.py.
#
# Pré-requisitos: AWS CLI v2 configurado (`aws configure`), `zip`, `python3`.
# Uso: ./deploy.sh
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJETO_DIR="$(dirname "$DIR")"
REGION="sa-east-1"
FUNCTION_NAME="djen-oab-sp-diario"
ROLE_NAME="djen-oab-sp-lambda-role"
SCHEDULE_NAME="djen-oab-sp-diario-5h59"
SCHEDULER_ROLE_NAME="djen-oab-sp-scheduler-role"
BUILD_DIR="$(mktemp -d)"
trap 'rm -rf "$BUILD_DIR"' EXIT

command -v aws >/dev/null || { echo "AWS CLI não encontrado: https://aws.amazon.com/cli/"; exit 1; }
command -v zip >/dev/null || { echo "Comando 'zip' não encontrado (instale via apt/brew)."; exit 1; }
aws sts get-caller-identity >/dev/null || { echo "AWS CLI não autenticado — rode 'aws configure'."; exit 1; }

echo "== 1/6 Config e segredos =="
set -a
source "$DIR/config.env"
set +a

ler_segredo() {
  local var_nome="$1" arquivo="$2"
  if [ -n "${!var_nome:-}" ]; then
    printf '%s' "${!var_nome}"
  elif [ -f "$PROJETO_DIR/$arquivo" ]; then
    tr -d '\n' < "$PROJETO_DIR/$arquivo"
  fi
}
export SENDGRID_API_KEY="$(ler_segredo SENDGRID_API_KEY .sendgrid_key)"
export TWILIO_ACCOUNT_SID="$(ler_segredo TWILIO_ACCOUNT_SID .twilio_sid)"
export TWILIO_AUTH_TOKEN="$(ler_segredo TWILIO_AUTH_TOKEN .twilio_token)"
export DJEN_SMTP_SENHA="$(ler_segredo DJEN_SMTP_SENHA .smtp_senha)"

if [ "${EMAIL_PROVEDOR:-}" = "sendgrid" ] && [ -z "$SENDGRID_API_KEY" ]; then
  echo "EMAIL_PROVEDOR=sendgrid mas SENDGRID_API_KEY não encontrada."
  echo "Defina a variável de ambiente ou crie ../.sendgrid_key"
  exit 1
fi
if [ "${EMAIL_PROVEDOR:-}" = "smtp" ] && [ -z "$DJEN_SMTP_SENHA" ]; then
  echo "EMAIL_PROVEDOR=smtp mas DJEN_SMTP_SENHA não encontrada."
  echo "Defina a variável de ambiente ou crie ../.smtp_senha"
  exit 1
fi
if [ "${WHATSAPP_HABILITADO:-}" = "true" ] && { [ -z "$TWILIO_ACCOUNT_SID" ] || [ -z "$TWILIO_AUTH_TOKEN" ]; }; then
  echo "WHATSAPP_HABILITADO=true mas faltam TWILIO_ACCOUNT_SID/TWILIO_AUTH_TOKEN."
  exit 1
fi

echo "== 2/6 Empacotando o código =="
cp "$DIR/lambda_handler.py" "$PROJETO_DIR/djen.py" "$PROJETO_DIR/notificacao.py" "$BUILD_DIR/"
(cd "$BUILD_DIR" && zip -q -r build.zip . -x 'trust-*.json' -x 'invoke-policy.json')
echo "Pacote pronto ($(du -h "$BUILD_DIR/build.zip" | cut -f1))."

echo "== 3/6 Role de execução da Lambda =="
if aws iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
  echo "Role $ROLE_NAME já existe."
else
  cat > "$BUILD_DIR/trust-lambda.json" <<'JSON'
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}
JSON
  aws iam create-role --role-name "$ROLE_NAME" \
    --assume-role-policy-document "file://$BUILD_DIR/trust-lambda.json" >/dev/null
  aws iam attach-role-policy --role-name "$ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
  echo "Role $ROLE_NAME criada. Aguardando propagação do IAM..."
  sleep 10
fi
ROLE_ARN="$(aws iam get-role --role-name "$ROLE_NAME" --query 'Role.Arn' --output text)"

echo "== 4/6 Função Lambda =="
AMBIENTE_JSON="$(python3 "$DIR/build_env_json.py")"
if aws lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" >/dev/null 2>&1; then
  echo "Função $FUNCTION_NAME já existe — atualizando código e configuração."
  aws lambda update-function-code --function-name "$FUNCTION_NAME" --region "$REGION" \
    --zip-file "fileb://$BUILD_DIR/build.zip" >/dev/null
  aws lambda wait function-updated --function-name "$FUNCTION_NAME" --region "$REGION"
  aws lambda update-function-configuration --function-name "$FUNCTION_NAME" --region "$REGION" \
    --timeout 60 --memory-size 256 --environment "$AMBIENTE_JSON" >/dev/null
  aws lambda wait function-updated --function-name "$FUNCTION_NAME" --region "$REGION"
else
  aws lambda create-function --function-name "$FUNCTION_NAME" --region "$REGION" \
    --runtime python3.12 --role "$ROLE_ARN" --handler lambda_handler.handler \
    --zip-file "fileb://$BUILD_DIR/build.zip" --timeout 60 --memory-size 256 \
    --environment "$AMBIENTE_JSON" >/dev/null
  echo "Função $FUNCTION_NAME criada em $REGION."
fi
FUNCTION_ARN="$(aws lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" \
  --query 'Configuration.FunctionArn' --output text)"

echo "== 5/6 Role do EventBridge Scheduler =="
if aws iam get-role --role-name "$SCHEDULER_ROLE_NAME" >/dev/null 2>&1; then
  echo "Role $SCHEDULER_ROLE_NAME já existe."
else
  cat > "$BUILD_DIR/trust-scheduler.json" <<'JSON'
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"scheduler.amazonaws.com"},"Action":"sts:AssumeRole"}]}
JSON
  aws iam create-role --role-name "$SCHEDULER_ROLE_NAME" \
    --assume-role-policy-document "file://$BUILD_DIR/trust-scheduler.json" >/dev/null
  echo "Role $SCHEDULER_ROLE_NAME criada. Aguardando propagação do IAM..."
  sleep 10
fi
SCHEDULER_ROLE_ARN="$(aws iam get-role --role-name "$SCHEDULER_ROLE_NAME" --query 'Role.Arn' --output text)"
cat > "$BUILD_DIR/invoke-policy.json" <<JSON
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":"lambda:InvokeFunction","Resource":"$FUNCTION_ARN"}]}
JSON
aws iam put-role-policy --role-name "$SCHEDULER_ROLE_NAME" \
  --policy-name invoke-djen-lambda --policy-document "file://$BUILD_DIR/invoke-policy.json"

echo "== 6/6 Agendamento (5:59, America/Sao_Paulo) =="
TARGET_JSON="{\"Arn\":\"$FUNCTION_ARN\",\"RoleArn\":\"$SCHEDULER_ROLE_ARN\"}"
if aws scheduler get-schedule --name "$SCHEDULE_NAME" --region "$REGION" >/dev/null 2>&1; then
  aws scheduler update-schedule --name "$SCHEDULE_NAME" --region "$REGION" \
    --schedule-expression "cron(59 5 * * ? *)" \
    --schedule-expression-timezone "America/Sao_Paulo" \
    --flexible-time-window '{"Mode":"OFF"}' \
    --target "$TARGET_JSON" >/dev/null
  echo "Agendamento $SCHEDULE_NAME atualizado."
else
  aws scheduler create-schedule --name "$SCHEDULE_NAME" --region "$REGION" \
    --schedule-expression "cron(59 5 * * ? *)" \
    --schedule-expression-timezone "America/Sao_Paulo" \
    --flexible-time-window '{"Mode":"OFF"}' \
    --target "$TARGET_JSON" >/dev/null
  echo "Agendamento $SCHEDULE_NAME criado — dispara todo dia às 5:59 (horário de Brasília)."
fi

echo
echo "Pronto. Função: $FUNCTION_ARN"
echo "Teste agora:   ./invocar_teste.sh"
echo "Ver logs:      aws logs tail /aws/lambda/$FUNCTION_NAME --region $REGION --since 1h"
echo "Remover tudo:  ./destroy.sh"
