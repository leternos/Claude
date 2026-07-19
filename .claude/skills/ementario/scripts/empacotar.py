#!/usr/bin/env python3
"""Empacota a skill para upload no Claude chat / cowork.

Uso:
    python3 scripts/empacotar.py   →  ementario.zip

Só a ferramenta entra no pacote — `entradas/` e `saidas/` ficam de fora, porque
o processo tramita em sigilo (art. 72, §2º, EAOAB).
"""

import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
INCLUIR = ("SKILL.md", "references", "scripts")


def itens() -> list[Path]:
    encontrados = []
    for nome in INCLUIR:
        alvo = RAIZ / nome
        if alvo.is_file():
            encontrados.append(alvo)
        else:
            encontrados += [
                p for p in sorted(alvo.rglob("*"))
                if p.is_file() and "__pycache__" not in p.parts
            ]
    return encontrados


def main() -> None:
    destino = RAIZ / "ementario.zip"
    arquivos = itens()
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        for arquivo in arquivos:
            z.write(arquivo, Path("ementario") / arquivo.relative_to(RAIZ))

    with zipfile.ZipFile(destino) as z:
        if z.testzip() is not None:
            raise SystemExit("zip corrompido")
        nomes = z.namelist()
    if "ementario/SKILL.md" not in nomes:
        raise SystemExit("pacote sem SKILL.md")

    print(f"{destino} — {destino.stat().st_size} bytes")
    for nome in nomes:
        print(f"  {nome}")


if __name__ == "__main__":
    main()
