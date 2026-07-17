#!/bin/sh
# Rode DENTRO do a-Shell, na pasta onde estão os 2 arquivos:
#   sh instalar-iphone-ashell.sh
DIR="$PWD"
P="$HOME/Documents/.profile"
touch "$P"
for cmd in decl conj trad sig cor; do
    linha="alias $cmd='python3 $DIR/familia_romana_standalone.py $cmd'"
    grep -qF "familia_romana_standalone.py $cmd" "$P" || echo "$linha" >> "$P"
done
grep -qF "alias fr=" "$P" || echo "alias fr='python3 $DIR/familia_romana_standalone.py'" >> "$P"
echo "Aliases gravados em ~/.profile. Feche e reabra o a-Shell e use:"
echo "  decl puella   |   conj ponere   |   trad villa"
