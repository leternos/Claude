#!/usr/bin/env bash
# Invoca a função agora mesmo (sem esperar as 5:59) para testar o deploy.
# Uso: ./invocar_teste.sh [AAAA-MM-DD]
set -euo pipefail
REGION="sa-east-1"
FUNCTION_NAME="djen-oab-sp-diario"
DATA="${1:-}"
SAIDA="$(mktemp)"

PAYLOAD="{}"
if [ -n "$DATA" ]; then
  PAYLOAD="{\"data\":\"$DATA\"}"
fi

aws lambda invoke --function-name "$FUNCTION_NAME" --region "$REGION" \
  --cli-read-timeout 90 --payload "$PAYLOAD" --cli-binary-format raw-in-base64-out \
  "$SAIDA" >/dev/null

echo "Resposta da função:"
cat "$SAIDA"; echo
rm -f "$SAIDA"

echo
echo "Logs recentes:"
aws logs tail "/aws/lambda/$FUNCTION_NAME" --region "$REGION" --since 5m || true
