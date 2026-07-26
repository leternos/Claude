#!/bin/bash
# Instala comandos curtos no Mac: decl, conj, trad, sig, cor, fr
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/.familia-romana"
BIN="$HOME/bin"
mkdir -p "$DEST" "$BIN"
cp "$DIR/familia_romana_standalone.py" "$DEST/"
cp "$DIR/familia_romana.db" "$DEST/" 2>/dev/null || true
chmod +x "$DEST/familia_romana_standalone.py"
for cmd in fr decl conj trad sig cor; do
    ln -sf "$DEST/familia_romana_standalone.py" "$BIN/$cmd"
done
RC="$HOME/.zshrc"
if ! grep -q 'HOME/bin' "$RC" 2>/dev/null; then
    echo 'export PATH="$HOME/bin:$PATH"' >> "$RC"
    echo "(PATH atualizado em ~/.zshrc)"
fi
echo "Instalado. Abra um terminal novo (ou rode: source ~/.zshrc) e use:"
echo "  decl puella   |   conj ponere   |   trad villa   |   cor \"frase\""
