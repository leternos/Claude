#!/usr/bin/env bash
# Remove tudo o que o deploy.sh criou na AWS (agendamento, função, roles).
# Uso: ./destroy.sh
set -uo pipefail

REGION="sa-east-1"
FUNCTION_NAME="djen-oab-sp-diario"
ROLE_NAME="djen-oab-sp-lambda-role"
SCHEDULE_NAME="djen-oab-sp-diario-5h59"
SCHEDULER_ROLE_NAME="djen-oab-sp-scheduler-role"

echo "Removendo agendamento..."
aws scheduler delete-schedule --name "$SCHEDULE_NAME" --region "$REGION" \
  && echo "  removido." || echo "  (já não existia)"

echo "Removendo função Lambda..."
aws lambda delete-function --function-name "$FUNCTION_NAME" --region "$REGION" \
  && echo "  removida." || echo "  (já não existia)"

echo "Removendo role do scheduler..."
aws iam delete-role-policy --role-name "$SCHEDULER_ROLE_NAME" --policy-name invoke-djen-lambda 2>/dev/null
aws iam delete-role --role-name "$SCHEDULER_ROLE_NAME" \
  && echo "  removida." || echo "  (já não existia)"

echo "Removendo role da Lambda..."
aws iam detach-role-policy --role-name "$ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole 2>/dev/null
aws iam delete-role --role-name "$ROLE_NAME" \
  && echo "  removida." || echo "  (já não existia)"

echo
echo "Pronto — nada permanece na AWS (e, dentro do Always Free, nada teria sido cobrado mesmo)."
