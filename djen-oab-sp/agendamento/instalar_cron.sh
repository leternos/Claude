#!/usr/bin/env bash
# Instala (ou atualiza) a entrada do crontab que roda a exportação diária às 5:59.
# Uso: ./agendamento/instalar_cron.sh   (a partir de qualquer diretório)
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$(command -v python3)"
LINHA="59 5 * * * cd $DIR && $PYTHON daily_export.py >> $DIR/exports/daily.log 2>&1"
MARCA="# djen-oab-sp"

mkdir -p "$DIR/exports"
( crontab -l 2>/dev/null | grep -v "$MARCA" ; echo "$LINHA $MARCA" ) | crontab -
echo "Agendado às 5:59 (horário local da máquina):"
echo "  $LINHA"
echo "Confira com: crontab -l"
