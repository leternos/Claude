#!/usr/bin/env python3
"""
Familia Romana — STANDALONE (iPhone/Mac) — 100% biblioteca padrão do Python

REGRAS IMPLEMENTADAS:
  1a) Respostas claras e objetivas, sem saudação.
  1b) Vocabulário do Familia Romana (Ørberg).
  1c) decl: singular e plural, todos os gêneros possíveis.
      Ordem: nominativo, genitivo, dativo, acusativo, ablativo.
      Tabela com singular e plural na mesma linha. UMA TABELA POR GÊNERO.
  1d) conj: informa a conjugação. Presente (ativa/passiva),
      Imperfeito (ativa/passiva), Futuro do presente (ativa/passiva).
  1e) Tabela na ordem: ego, tu, is, nos, vos, ii.
  1f) trad/decl: informa a declinação e, se substantivo, o gênero.
  1g) Se não souber, DIZ. Não inventa.
  1h) cor: o que está certo, o que está errado, versão consolidada.
  2)  Comandos: decl, conj, trad|sig, cor (com ou sem '/').

Uso (zero dependências, zero pip, zero servidor):
  python3 familia_romana_standalone.py decl puella
  python3 familia_romana_standalone.py conj ponere
  python3 familia_romana_standalone.py               # modo interativo

  Se familia_romana.db estiver na MESMA pasta: trad ganha exemplos do
  livro e cor valida contra as 7.566 formas. Sem o .db, decl/conj/trad
  funcionam igual (só sem exemplos).
"""

import re
import sqlite3
import unicodedata
from pathlib import Path
from typing import Optional, Dict, List

DB_PATH = Path(__file__).resolve().parent / 'familia_romana.db'

# ============================================================================
# Normalização
# ============================================================================

def _strip_macrons(s: str) -> str:
    """Remove macrons/diacríticos para chave de busca: pōnō → pono"""
    nfkd = unicodedata.normalize('NFD', s.lower().strip())
    return ''.join(c for c in nfkd if not unicodedata.combining(c))

# ============================================================================
# SUBSTANTIVOS — vocabulário do Familia Romana
# chave normalizada → {lema, radical, decl, gen, trad}
# decl: '1', '2us', '2r', '2n', '3', '3i', '3n', '3ni'
# ============================================================================

SUBSTANTIVOS = {
    # ---- 1ª declinação (femininos) ----
    'puella':   {'lema': 'puella',   'rad': 'puell',   'decl': '1',  'gen': 'f', 'trad': 'menina'},
    'femina':   {'lema': 'fēmina',   'rad': 'fēmin',   'decl': '1',  'gen': 'f', 'trad': 'mulher'},
    'domina':   {'lema': 'domina',   'rad': 'domin',   'decl': '1',  'gen': 'f', 'trad': 'senhora, dona'},
    'filia':    {'lema': 'fīlia',    'rad': 'fīli',    'decl': '1',  'gen': 'f', 'trad': 'filha'},
    'familia':  {'lema': 'familia',  'rad': 'famili',  'decl': '1',  'gen': 'f', 'trad': 'família'},
    'insula':   {'lema': 'īnsula',   'rad': 'īnsul',   'decl': '1',  'gen': 'f', 'trad': 'ilha'},
    'via':      {'lema': 'via',      'rad': 'vi',      'decl': '1',  'gen': 'f', 'trad': 'via, caminho, estrada'},
    'rosa':     {'lema': 'rosa',     'rad': 'ros',     'decl': '1',  'gen': 'f', 'trad': 'rosa'},
    'villa':    {'lema': 'vīlla',    'rad': 'vīll',    'decl': '1',  'gen': 'f', 'trad': 'casa de campo, vila'},
    'ancilla':  {'lema': 'ancilla',  'rad': 'ancill',  'decl': '1',  'gen': 'f', 'trad': 'escrava, criada'},
    'epistula': {'lema': 'epistula', 'rad': 'epistul', 'decl': '1',  'gen': 'f', 'trad': 'carta'},
    'pecunia':  {'lema': 'pecūnia',  'rad': 'pecūni',  'decl': '1',  'gen': 'f', 'trad': 'dinheiro'},
    'littera':  {'lema': 'littera',  'rad': 'litter',  'decl': '1',  'gen': 'f', 'trad': 'letra; (pl.) carta'},
    'aqua':     {'lema': 'aqua',     'rad': 'aqu',     'decl': '1',  'gen': 'f', 'trad': 'água'},
    'terra':    {'lema': 'terra',    'rad': 'terr',    'decl': '1',  'gen': 'f', 'trad': 'terra'},
    'mensa':    {'lema': 'mēnsa',    'rad': 'mēns',    'decl': '1',  'gen': 'f', 'trad': 'mesa'},
    'pagina':   {'lema': 'pāgina',   'rad': 'pāgin',   'decl': '1',  'gen': 'f', 'trad': 'página'},
    'provincia':{'lema': 'prōvincia','rad': 'prōvinci','decl': '1',  'gen': 'f', 'trad': 'província'},

    # ---- 2ª declinação, masculinos em -us ----
    'servus':   {'lema': 'servus',   'rad': 'serv',    'decl': '2us','gen': 'm', 'trad': 'escravo, servo'},
    'dominus':  {'lema': 'dominus',  'rad': 'domin',   'decl': '2us','gen': 'm', 'trad': 'senhor, dono'},
    'filius':   {'lema': 'fīlius',   'rad': 'fīli',    'decl': '2us','gen': 'm', 'trad': 'filho'},
    'amicus':   {'lema': 'amīcus',   'rad': 'amīc',    'decl': '2us','gen': 'm', 'trad': 'amigo'},
    'equus':    {'lema': 'equus',    'rad': 'equ',     'decl': '2us','gen': 'm', 'trad': 'cavalo'},
    'hortus':   {'lema': 'hortus',   'rad': 'hort',    'decl': '2us','gen': 'm', 'trad': 'jardim'},
    'maritus':  {'lema': 'marītus',  'rad': 'marīt',   'decl': '2us','gen': 'm', 'trad': 'marido'},
    'nummus':   {'lema': 'nummus',   'rad': 'numm',    'decl': '2us','gen': 'm', 'trad': 'moeda'},
    'sacculus': {'lema': 'sacculus', 'rad': 'saccul',  'decl': '2us','gen': 'm', 'trad': 'bolsinha, saquinho'},
    'oculus':   {'lema': 'oculus',   'rad': 'ocul',    'decl': '2us','gen': 'm', 'trad': 'olho'},
    'digitus':  {'lema': 'digitus',  'rad': 'digit',   'decl': '2us','gen': 'm', 'trad': 'dedo'},
    'fluvius':  {'lema': 'fluvius',  'rad': 'fluvi',   'decl': '2us','gen': 'm', 'trad': 'rio'},
    'numerus':  {'lema': 'numerus',  'rad': 'numer',   'decl': '2us','gen': 'm', 'trad': 'número'},
    'titulus':  {'lema': 'titulus',  'rad': 'titul',   'decl': '2us','gen': 'm', 'trad': 'título'},

    # ---- 2ª declinação, masculinos em -er / vir ----
    'puer':     {'lema': 'puer',     'rad': 'puer',    'decl': '2r', 'gen': 'm', 'trad': 'menino'},
    'vir':      {'lema': 'vir',      'rad': 'vir',     'decl': '2r', 'gen': 'm', 'trad': 'homem, marido'},
    'liber':    {'lema': 'liber',    'rad': 'libr',    'decl': '2r', 'gen': 'm', 'trad': 'livro'},
    'ager':     {'lema': 'ager',     'rad': 'agr',     'decl': '2r', 'gen': 'm', 'trad': 'campo'},
    'magister': {'lema': 'magister', 'rad': 'magistr', 'decl': '2r', 'gen': 'm', 'trad': 'professor, mestre'},

    # ---- 2ª declinação, neutros ----
    'oppidum':  {'lema': 'oppidum',  'rad': 'oppid',   'decl': '2n', 'gen': 'n', 'trad': 'cidade (fortificada)'},
    'verbum':   {'lema': 'verbum',   'rad': 'verb',    'decl': '2n', 'gen': 'n', 'trad': 'palavra, verbo'},
    'periculum':{'lema': 'perīculum','rad': 'perīcul', 'decl': '2n', 'gen': 'n', 'trad': 'perigo'},
    'baculum':  {'lema': 'baculum',  'rad': 'bacul',   'decl': '2n', 'gen': 'n', 'trad': 'bastão, bengala'},
    'vocabulum':{'lema': 'vocābulum','rad': 'vocābul', 'decl': '2n', 'gen': 'n', 'trad': 'vocábulo, palavra'},
    'capitulum':{'lema': 'capitulum','rad': 'capitul', 'decl': '2n', 'gen': 'n', 'trad': 'capítulo'},
    'exemplum': {'lema': 'exemplum', 'rad': 'exempl',  'decl': '2n', 'gen': 'n', 'trad': 'exemplo'},
    'imperium': {'lema': 'imperium', 'rad': 'imperi',  'decl': '2n', 'gen': 'n', 'trad': 'império; ordem'},
    'ostium':   {'lema': 'ōstium',   'rad': 'ōsti',    'decl': '2n', 'gen': 'n', 'trad': 'porta, entrada'},
    'cubiculum':{'lema': 'cubiculum','rad': 'cubicul', 'decl': '2n', 'gen': 'n', 'trad': 'quarto de dormir'},

    # ---- 3ª declinação, m/f (tema consonantal) ----
    'rex':      {'lema': 'rēx',      'rad': 'rēg',     'decl': '3',  'gen': 'm', 'trad': 'rei'},
    'lex':      {'lema': 'lēx',      'rad': 'lēg',     'decl': '3',  'gen': 'f', 'trad': 'lei'},
    'pax':      {'lema': 'pāx',      'rad': 'pāc',     'decl': '3',  'gen': 'f', 'trad': 'paz'},
    'vox':      {'lema': 'vōx',      'rad': 'vōc',     'decl': '3',  'gen': 'f', 'trad': 'voz'},
    'miles':    {'lema': 'mīles',    'rad': 'mīlit',   'decl': '3',  'gen': 'm', 'trad': 'soldado'},
    'pater':    {'lema': 'pater',    'rad': 'patr',    'decl': '3',  'gen': 'm', 'trad': 'pai'},
    'mater':    {'lema': 'māter',    'rad': 'mātr',    'decl': '3',  'gen': 'f', 'trad': 'mãe'},
    'frater':   {'lema': 'frāter',   'rad': 'frātr',   'decl': '3',  'gen': 'm', 'trad': 'irmão'},
    'soror':    {'lema': 'soror',    'rad': 'sorōr',   'decl': '3',  'gen': 'f', 'trad': 'irmã'},
    'homo':     {'lema': 'homō',     'rad': 'homin',   'decl': '3',  'gen': 'm', 'trad': 'ser humano, homem'},
    'leo':      {'lema': 'leō',      'rad': 'leōn',    'decl': '3',  'gen': 'm', 'trad': 'leão'},
    'pastor':   {'lema': 'pāstor',   'rad': 'pāstōr',  'decl': '3',  'gen': 'm', 'trad': 'pastor'},
    'sol':      {'lema': 'sōl',      'rad': 'sōl',     'decl': '3',  'gen': 'm', 'trad': 'sol'},

    # ---- 3ª declinação, m/f i-stem (gen. pl. -ium) ----
    'urbs':     {'lema': 'urbs',     'rad': 'urb',     'decl': '3i', 'gen': 'f', 'trad': 'cidade'},
    'nox':      {'lema': 'nox',      'rad': 'noct',    'decl': '3i', 'gen': 'f', 'trad': 'noite'},
    'ovis':     {'lema': 'ovis',     'rad': 'ov',      'decl': '3i', 'gen': 'f', 'trad': 'ovelha'},
    'mensis':   {'lema': 'mēnsis',   'rad': 'mēns',    'decl': '3i', 'gen': 'm', 'trad': 'mês'},
    'canis':    {'lema': 'canis',    'rad': 'can',     'decl': '3',  'gen': 'm', 'trad': 'cão'},  # gen. pl. canum (exceção)

    # ---- 3ª declinação, neutros ----
    'nomen':    {'lema': 'nōmen',    'rad': 'nōmin',   'decl': '3n', 'gen': 'n', 'trad': 'nome'},
    'flumen':   {'lema': 'flūmen',   'rad': 'flūmin',  'decl': '3n', 'gen': 'n', 'trad': 'rio'},
    'corpus':   {'lema': 'corpus',   'rad': 'corpor',  'decl': '3n', 'gen': 'n', 'trad': 'corpo'},
    'tempus':   {'lema': 'tempus',   'rad': 'tempor',  'decl': '3n', 'gen': 'n', 'trad': 'tempo'},
    'caput':    {'lema': 'caput',    'rad': 'capit',   'decl': '3n', 'gen': 'n', 'trad': 'cabeça'},
    'mare':     {'lema': 'mare',     'rad': 'mar',     'decl': '3ni','gen': 'n', 'trad': 'mar'},
}

# ============================================================================
# ADJETIVOS — declinam em TODOS os gêneros (uma tabela por gênero)
# tipo: '12' (1ª/2ª: -us/-a/-um), '12r' (-er/-ra/-rum), '3-2' (3ª, 2 term.)
# ============================================================================

ADJETIVOS = {
    'magnus':   {'lema': 'magnus',   'rad': 'magn',    'tipo': '12',  'trad': 'grande'},
    'parvus':   {'lema': 'parvus',   'rad': 'parv',    'tipo': '12',  'trad': 'pequeno'},
    'bonus':    {'lema': 'bonus',    'rad': 'bon',     'tipo': '12',  'trad': 'bom'},
    'malus':    {'lema': 'malus',    'rad': 'mal',     'tipo': '12',  'trad': 'mau'},
    'novus':    {'lema': 'novus',    'rad': 'nov',     'tipo': '12',  'trad': 'novo'},
    'antiquus': {'lema': 'antīquus', 'rad': 'antīqu',  'tipo': '12',  'trad': 'antigo'},
    'longus':   {'lema': 'longus',   'rad': 'long',    'tipo': '12',  'trad': 'longo, comprido'},
    'latus':    {'lema': 'lātus',    'rad': 'lāt',     'tipo': '12',  'trad': 'largo'},
    'altus':    {'lema': 'altus',    'rad': 'alt',     'tipo': '12',  'trad': 'alto; profundo'},
    'foedus':   {'lema': 'foedus',   'rad': 'foed',    'tipo': '12',  'trad': 'feio'},
    'probus':   {'lema': 'probus',   'rad': 'prob',    'tipo': '12',  'trad': 'honesto, bom'},
    'improbus': {'lema': 'improbus', 'rad': 'improb',  'tipo': '12',  'trad': 'mau, malvado'},
    'iratus':   {'lema': 'īrātus',   'rad': 'īrāt',    'tipo': '12',  'trad': 'irado, zangado'},
    'laetus':   {'lema': 'laetus',   'rad': 'laet',    'tipo': '12',  'trad': 'alegre'},
    'romanus':  {'lema': 'Rōmānus',  'rad': 'Rōmān',   'tipo': '12',  'trad': 'romano'},
    'graecus':  {'lema': 'Graecus',  'rad': 'Graec',   'tipo': '12',  'trad': 'grego'},
    'multus':   {'lema': 'multus',   'rad': 'mult',    'tipo': '12',  'trad': 'muito'},
    'paucus':   {'lema': 'paucus',   'rad': 'pauc',    'tipo': '12',  'trad': 'pouco'},
    'pulcher':  {'lema': 'pulcher',  'rad': 'pulchr',  'tipo': '12r', 'trad': 'belo, bonito'},
    'omnis':    {'lema': 'omnis',    'rad': 'omn',     'tipo': '3-2', 'trad': 'todo, cada'},
    'brevis':   {'lema': 'brevis',   'rad': 'brev',    'tipo': '3-2', 'trad': 'breve, curto'},
    'gravis':   {'lema': 'gravis',   'rad': 'grav',    'tipo': '3-2', 'trad': 'pesado, grave'},
    'levis':    {'lema': 'levis',    'rad': 'lev',     'tipo': '3-2', 'trad': 'leve'},
    'fortis':   {'lema': 'fortis',   'rad': 'fort',    'tipo': '3-2', 'trad': 'forte, corajoso'},
}

# ============================================================================
# VERBOS — vocabulário do Familia Romana
# conj: '1', '2', '3', '3io', '4'
# intrans: True → passiva só impessoal (nota, não inventa formas pessoais)
# ============================================================================

VERBOS = {
    # 1ª conjugação
    'amo':        {'lema': 'amāre',       'rad': 'am',       'conj': '1', 'trad': 'amar'},
    'habito':     {'lema': 'habitāre',    'rad': 'habit',    'conj': '1', 'trad': 'morar, habitar'},
    'canto':      {'lema': 'cantāre',     'rad': 'cant',     'conj': '1', 'trad': 'cantar'},
    'voco':       {'lema': 'vocāre',      'rad': 'voc',      'conj': '1', 'trad': 'chamar'},
    'pulso':      {'lema': 'pulsāre',     'rad': 'puls',     'conj': '1', 'trad': 'bater (em)'},
    'ploro':      {'lema': 'plōrāre',     'rad': 'plōr',     'conj': '1', 'trad': 'chorar'},
    'interrogo':  {'lema': 'interrogāre', 'rad': 'interrog', 'conj': '1', 'trad': 'perguntar'},
    'numero':     {'lema': 'numerāre',    'rad': 'numer',    'conj': '1', 'trad': 'contar'},
    'porto':      {'lema': 'portāre',     'rad': 'port',     'conj': '1', 'trad': 'carregar, levar'},
    'intro':      {'lema': 'intrāre',     'rad': 'intr',     'conj': '1', 'trad': 'entrar'},
    'ambulo':     {'lema': 'ambulāre',    'rad': 'ambul',    'conj': '1', 'trad': 'andar, passear', 'intrans': True},
    'laudo':      {'lema': 'laudāre',     'rad': 'laud',     'conj': '1', 'trad': 'louvar, elogiar'},

    # 2ª conjugação
    'habeo':      {'lema': 'habēre',      'rad': 'hab',      'conj': '2', 'trad': 'ter'},
    'video':      {'lema': 'vidēre',      'rad': 'vid',      'conj': '2', 'trad': 'ver'},
    'respondeo':  {'lema': 'respondēre',  'rad': 'respond',  'conj': '2', 'trad': 'responder'},
    'rideo':      {'lema': 'rīdēre',      'rad': 'rīd',      'conj': '2', 'trad': 'rir'},
    'taceo':      {'lema': 'tacēre',      'rad': 'tac',      'conj': '2', 'trad': 'calar-se', 'intrans': True},
    'pareo':      {'lema': 'pārēre',      'rad': 'pār',      'conj': '2', 'trad': 'obedecer', 'intrans': True},
    'timeo':      {'lema': 'timēre',      'rad': 'tim',      'conj': '2', 'trad': 'temer'},
    'teneo':      {'lema': 'tenēre',      'rad': 'ten',      'conj': '2', 'trad': 'segurar, ter'},
    'moneo':      {'lema': 'monēre',      'rad': 'mon',      'conj': '2', 'trad': 'advertir, avisar'},

    # 3ª conjugação
    'lego':       {'lema': 'legere',      'rad': 'leg',      'conj': '3', 'trad': 'ler'},
    'dico':       {'lema': 'dīcere',      'rad': 'dīc',      'conj': '3', 'trad': 'dizer'},
    'pono':       {'lema': 'pōnere',      'rad': 'pōn',      'conj': '3', 'trad': 'colocar, pôr'},
    'sumo':       {'lema': 'sūmere',      'rad': 'sūm',      'conj': '3', 'trad': 'pegar, tomar'},
    'scribo':     {'lema': 'scrībere',    'rad': 'scrīb',    'conj': '3', 'trad': 'escrever'},
    'discedo':    {'lema': 'discēdere',   'rad': 'discēd',   'conj': '3', 'trad': 'partir, ir embora', 'intrans': True},
    'claudo':     {'lema': 'claudere',    'rad': 'claud',    'conj': '3', 'trad': 'fechar'},
    'verto':      {'lema': 'vertere',     'rad': 'vert',     'conj': '3', 'trad': 'virar, voltar'},
    'curro':      {'lema': 'currere',     'rad': 'curr',     'conj': '3', 'trad': 'correr', 'intrans': True},
    'bibo':       {'lema': 'bibere',      'rad': 'bib',      'conj': '3', 'trad': 'beber'},
    'emo':        {'lema': 'emere',       'rad': 'em',       'conj': '3', 'trad': 'comprar'},
    'vendo':      {'lema': 'vēndere',     'rad': 'vēnd',     'conj': '3', 'trad': 'vender'},
    'mitto':      {'lema': 'mittere',     'rad': 'mitt',     'conj': '3', 'trad': 'enviar, mandar'},
    'peto':       {'lema': 'petere',      'rad': 'pet',      'conj': '3', 'trad': 'dirigir-se a; pedir'},
    'quaero':     {'lema': 'quaerere',    'rad': 'quaer',    'conj': '3', 'trad': 'procurar; perguntar'},
    'ago':        {'lema': 'agere',       'rad': 'ag',       'conj': '3', 'trad': 'fazer, agir; conduzir'},
    'vivo':       {'lema': 'vīvere',      'rad': 'vīv',      'conj': '3', 'trad': 'viver', 'intrans': True},

    # 3ª conjugação em -iō
    'facio':      {'lema': 'facere',      'rad': 'fac',      'conj': '3io', 'trad': 'fazer', 'pas_supletiva': 'fīō, fierī'},
    'capio':      {'lema': 'capere',      'rad': 'cap',      'conj': '3io', 'trad': 'pegar, capturar'},
    'accipio':    {'lema': 'accipere',    'rad': 'accip',    'conj': '3io', 'trad': 'receber'},
    'aspicio':    {'lema': 'aspicere',    'rad': 'aspic',    'conj': '3io', 'trad': 'olhar para'},
    'fugio':      {'lema': 'fugere',      'rad': 'fug',      'conj': '3io', 'trad': 'fugir', 'intrans': True},

    # 4ª conjugação
    'venio':      {'lema': 'venīre',      'rad': 'ven',      'conj': '4', 'trad': 'vir', 'intrans': True},
    'audio':      {'lema': 'audīre',      'rad': 'aud',      'conj': '4', 'trad': 'ouvir'},
    'dormio':     {'lema': 'dormīre',     'rad': 'dorm',     'conj': '4', 'trad': 'dormir', 'intrans': True},
    'aperio':     {'lema': 'aperīre',     'rad': 'aper',     'conj': '4', 'trad': 'abrir'},
    'punio':      {'lema': 'pūnīre',      'rad': 'pūn',      'conj': '4', 'trad': 'punir'},
    'scio':       {'lema': 'scīre',       'rad': 'sc',       'conj': '4', 'trad': 'saber'},
}

# Aliases: infinitivo → chave da 1ª pessoa
_VERBO_ALIASES = {}
for _k, _v in VERBOS.items():
    _VERBO_ALIASES[_strip_macrons(_v['lema'])] = _k   # 'ponere' → 'pono'
    _VERBO_ALIASES[_k] = _k                            # 'pono'   → 'pono'

# ============================================================================
# PARADIGMAS DE DECLINAÇÃO
# Cada função devolve dict caso → (singular, plural) com FORMAS COMPLETAS.
# Ordem fixa: nom, gen, dat, acc, abl  (instrução 1c)
# ============================================================================

CASOS = ['nom', 'gen', 'dat', 'acc', 'abl']
CASOS_NOME = {'nom': 'Nominativo', 'gen': 'Genitivo', 'dat': 'Dativo',
              'acc': 'Acusativo', 'abl': 'Ablativo'}

def _decl_1(rad, nom_sg=None):
    return {
        'nom': (nom_sg or rad + 'a', rad + 'ae'),
        'gen': (rad + 'ae',  rad + 'ārum'),
        'dat': (rad + 'ae',  rad + 'īs'),
        'acc': (rad + 'am',  rad + 'ās'),
        'abl': (rad + 'ā',   rad + 'īs'),
    }

def _decl_2us(rad, nom_sg=None):
    return {
        'nom': (nom_sg or rad + 'us', rad + 'ī'),
        'gen': (rad + 'ī',   rad + 'ōrum'),
        'dat': (rad + 'ō',   rad + 'īs'),
        'acc': (rad + 'um',  rad + 'ōs'),
        'abl': (rad + 'ō',   rad + 'īs'),
    }

def _decl_2r(rad, nom_sg):
    # nom. sg. próprio (puer, liber, vir); demais casos sobre o radical
    return {
        'nom': (nom_sg,      rad + 'ī'),
        'gen': (rad + 'ī',   rad + 'ōrum'),
        'dat': (rad + 'ō',   rad + 'īs'),
        'acc': (rad + 'um',  rad + 'ōs'),
        'abl': (rad + 'ō',   rad + 'īs'),
    }

def _decl_2n(rad, nom_sg=None):
    return {
        'nom': (nom_sg or rad + 'um', rad + 'a'),
        'gen': (rad + 'ī',   rad + 'ōrum'),
        'dat': (rad + 'ō',   rad + 'īs'),
        'acc': (nom_sg or rad + 'um', rad + 'a'),
        'abl': (rad + 'ō',   rad + 'īs'),
    }

def _decl_3(rad, nom_sg, gen_pl=None):
    return {
        'nom': (nom_sg,       rad + 'ēs'),
        'gen': (rad + 'is',   gen_pl or rad + 'um'),
        'dat': (rad + 'ī',    rad + 'ibus'),
        'acc': (rad + 'em',   rad + 'ēs'),
        'abl': (rad + 'e',    rad + 'ibus'),
    }

def _decl_3i(rad, nom_sg):
    return _decl_3(rad, nom_sg, gen_pl=rad + 'ium')

def _decl_3n(rad, nom_sg):
    return {
        'nom': (nom_sg,       rad + 'a'),
        'gen': (rad + 'is',   rad + 'um'),
        'dat': (rad + 'ī',    rad + 'ibus'),
        'acc': (nom_sg,       rad + 'a'),
        'abl': (rad + 'e',    rad + 'ibus'),
    }

def _decl_3ni(rad, nom_sg):
    # neutro i-stem (mare): abl. sg. -ī, pl. -ia/-ium
    return {
        'nom': (nom_sg,       rad + 'ia'),
        'gen': (rad + 'is',   rad + 'ium'),
        'dat': (rad + 'ī',    rad + 'ibus'),
        'acc': (nom_sg,       rad + 'ia'),
        'abl': (rad + 'ī',    rad + 'ibus'),
    }

def _decl_3adj_mf(rad, nom_sg):
    # adjetivo 3ª, 2 terminações — masc/fem (abl. sg. -ī, gen. pl. -ium)
    return {
        'nom': (nom_sg,       rad + 'ēs'),
        'gen': (rad + 'is',   rad + 'ium'),
        'dat': (rad + 'ī',    rad + 'ibus'),
        'acc': (rad + 'em',   rad + 'ēs'),
        'abl': (rad + 'ī',    rad + 'ibus'),
    }

def _decl_3adj_n(rad):
    return {
        'nom': (rad + 'e',    rad + 'ia'),
        'gen': (rad + 'is',   rad + 'ium'),
        'dat': (rad + 'ī',    rad + 'ibus'),
        'acc': (rad + 'e',    rad + 'ia'),
        'abl': (rad + 'ī',    rad + 'ibus'),
    }

_DECL_FUNCS = {
    '1': _decl_1, '2us': _decl_2us, '2r': _decl_2r, '2n': _decl_2n,
    '3': _decl_3, '3i': _decl_3i, '3n': _decl_3n, '3ni': _decl_3ni,
}

_DECL_LABEL = {
    '1': '1ª declinação', '2us': '2ª declinação', '2r': '2ª declinação',
    '2n': '2ª declinação', '3': '3ª declinação', '3i': '3ª declinação',
    '3n': '3ª declinação', '3ni': '3ª declinação',
}

_GEN_LABEL = {'m': 'masculino', 'f': 'feminino', 'n': 'neutro'}

# ============================================================================
# PARADIGMAS DE CONJUGAÇÃO
# Terminações completas anexadas ao radical.
# Ordem fixa das pessoas: ego, tu, is, nos, vos, ii  (instrução 1e)
# ============================================================================

PESSOAS_HEADER = ['Ego', 'Tu', 'Is/Ea/Id', 'Nos', 'Vos', 'Iī/Eae/Ea']

PARADIGMAS_VERBAIS = {
    '1': {
        'pres_at':  ['ō',    'ās',    'at',    'āmus',   'ātis',   'ant'],
        'pres_pas': ['or',   'āris',  'ātur',  'āmur',   'āminī',  'antur'],
        'impf_at':  ['ābam', 'ābās',  'ābat',  'ābāmus', 'ābātis', 'ābant'],
        'impf_pas': ['ābar', 'ābāris','ābātur','ābāmur', 'ābāminī','ābantur'],
        'fut_at':   ['ābō',  'ābis',  'ābit',  'ābimus', 'ābitis', 'ābunt'],
        'fut_pas':  ['ābor', 'āberis','ābitur','ābimur', 'ābiminī','ābuntur'],
    },
    '2': {
        'pres_at':  ['eō',   'ēs',    'et',    'ēmus',   'ētis',   'ent'],
        'pres_pas': ['eor',  'ēris',  'ētur',  'ēmur',   'ēminī',  'entur'],
        'impf_at':  ['ēbam', 'ēbās',  'ēbat',  'ēbāmus', 'ēbātis', 'ēbant'],
        'impf_pas': ['ēbar', 'ēbāris','ēbātur','ēbāmur', 'ēbāminī','ēbantur'],
        'fut_at':   ['ēbō',  'ēbis',  'ēbit',  'ēbimus', 'ēbitis', 'ēbunt'],
        'fut_pas':  ['ēbor', 'ēberis','ēbitur','ēbimur', 'ēbiminī','ēbuntur'],
    },
    '3': {
        'pres_at':  ['ō',    'is',    'it',    'imus',   'itis',   'unt'],
        'pres_pas': ['or',   'eris',  'itur',  'imur',   'iminī',  'untur'],
        'impf_at':  ['ēbam', 'ēbās',  'ēbat',  'ēbāmus', 'ēbātis', 'ēbant'],
        'impf_pas': ['ēbar', 'ēbāris','ēbātur','ēbāmur', 'ēbāminī','ēbantur'],
        'fut_at':   ['am',   'ēs',    'et',    'ēmus',   'ētis',   'ent'],
        'fut_pas':  ['ar',   'ēris',  'ētur',  'ēmur',   'ēminī',  'entur'],
    },
    '3io': {
        'pres_at':  ['iō',   'is',    'it',    'imus',   'itis',   'iunt'],
        'pres_pas': ['ior',  'eris',  'itur',  'imur',   'iminī',  'iuntur'],
        'impf_at':  ['iēbam','iēbās', 'iēbat', 'iēbāmus','iēbātis','iēbant'],
        'impf_pas': ['iēbar','iēbāris','iēbātur','iēbāmur','iēbāminī','iēbantur'],
        'fut_at':   ['iam',  'iēs',   'iet',   'iēmus',  'iētis',  'ient'],
        'fut_pas':  ['iar',  'iēris', 'iētur', 'iēmur',  'iēminī', 'ientur'],
    },
    '4': {
        'pres_at':  ['iō',   'īs',    'it',    'īmus',   'ītis',   'iunt'],
        'pres_pas': ['ior',  'īris',  'ītur',  'īmur',   'īminī',  'iuntur'],
        'impf_at':  ['iēbam','iēbās', 'iēbat', 'iēbāmus','iēbātis','iēbant'],
        'impf_pas': ['iēbar','iēbāris','iēbātur','iēbāmur','iēbāminī','iēbantur'],
        'fut_at':   ['iam',  'iēs',   'iet',   'iēmus',  'iētis',  'ient'],
        'fut_pas':  ['iar',  'iēris', 'iētur', 'iēmur',  'iēminī', 'ientur'],
    },
}

_CONJ_LABEL = {'1': '1ª conjugação', '2': '2ª conjugação',
               '3': '3ª conjugação', '3io': '3ª conjugação (em -iō)',
               '4': '4ª conjugação'}

_TEMPOS = [
    ('pres_at',  'Presente (Ativa)'),
    ('pres_pas', 'Presente (Passiva)'),
    ('impf_at',  'Imperfeito (Ativa)'),
    ('impf_pas', 'Imperfeito (Passiva)'),
    ('fut_at',   'Futuro (Ativa)'),
    ('fut_pas',  'Futuro (Passiva)'),
]

# ============================================================================
# RENDERIZADORES
# ============================================================================

def _render_tabela_decl(titulo_genero: str, formas: Dict) -> str:
    """Tabela por gênero: Caso | Singular | Plural (mesma linha)."""
    out = f"**{titulo_genero}**\n\n"
    out += "| Caso | Singular | Plural |\n|---|---|---|\n"
    for caso in CASOS:
        sg, pl = formas[caso]
        out += f"| {CASOS_NOME[caso]} | {sg} | {pl} |\n"
    return out

def _render_tabela_conj(dados_verbo: Dict) -> str:
    rad = dados_verbo['rad']
    conj = dados_verbo['conj']
    par = PARADIGMAS_VERBAIS[conj]
    intrans = dados_verbo.get('intrans', False)
    pas_supl = dados_verbo.get('pas_supletiva')

    out = "| | " + " | ".join(PESSOAS_HEADER) + " |\n"
    out += "|---|" + "---|" * 6 + "\n"
    notas = []

    for chave, label in _TEMPOS:
        passiva = chave.endswith('_pas')
        if passiva and pas_supl:
            out += f"| **{label}** | — | — | — | — | — | — |\n"
            if 'supl' not in notas:
                notas.append('supl')
            continue
        if passiva and intrans:
            impessoal = rad + par[chave][2]  # 3ª pessoa do singular
            out += f"| **{label}** | — | — | {impessoal}* | — | — | — |\n"
            if 'intrans' not in notas:
                notas.append('intrans')
            continue
        formas = [rad + t for t in par[chave]]
        out += f"| **{label}** | " + " | ".join(formas) + " |\n"

    if 'intrans' in notas:
        out += ("\n\\* Verbo intransitivo: a voz passiva só ocorre de forma "
                "impessoal (3ª pessoa do singular).\n")
    if 'supl' in notas:
        out += (f"\nA voz passiva de **{dados_verbo['lema']}** no sistema do "
                f"presente não é regular: usa-se **{pas_supl}**.\n")
    return out

# ============================================================================
# PROCESSADOR
# ============================================================================

class FamiliaRomanaProcessor:

    # ---------- Banco local (exemplos do livro) ----------

    def _db_lookup_contextos(self, chave: str) -> Optional[str]:
        """Consulta direta ao familia_romana.db (se existir ao lado do script)."""
        if not DB_PATH.exists():
            return None
        try:
            conn = sqlite3.connect(str(DB_PATH))
            cur = conn.cursor()
            cur.execute('SELECT contextos FROM vocabulum WHERE palavra = ?',
                        (chave,))
            row = cur.fetchone()
            conn.close()
            return row[0] if row and row[0] else None
        except sqlite3.Error:
            return None

    def _exemplos_do_livro(self, palavra: str, n: int = 2) -> List[str]:
        """Busca até n exemplos reais no banco do Familia Romana."""
        ctx = self._db_lookup_contextos(_strip_macrons(palavra))
        if not ctx:
            return []
        return [c.strip() for c in ctx.split(' | ') if c.strip()][:n]

    # ---------- comandos ----------

    def process_command(self, command_line: str) -> str:
        command_line = command_line.strip()
        if command_line.startswith('/'):
            command_line = command_line[1:]

        parts = command_line.split(maxsplit=1)
        if not parts:
            return "Formato: decl|conj|trad|sig|cor <palavra ou frase>"
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ''

        if cmd == 'decl':
            if not arg:
                return "Formato: decl <palavra>"
            return self._declinar(arg)
        if cmd == 'conj':
            if not arg:
                return "Formato: conj <verbo>"
            return self._conjugar(arg)
        if cmd in ('trad', 'sig'):
            if not arg:
                return "Formato: trad <palavra>"
            return self._traduzir(arg)
        if cmd == 'cor':
            if not arg:
                return "Formato: cor <frase>"
            return self._corrigir(arg)
        return f"Comando desconhecido: '{cmd}'. Use decl, conj, trad, sig ou cor."

    # ---------- decl ----------

    def _declinar(self, palavra: str) -> str:
        chave = _strip_macrons(palavra)

        # Substantivo: um gênero (o da palavra) → uma tabela
        if chave in SUBSTANTIVOS:
            d = SUBSTANTIVOS[chave]
            formas = _DECL_FUNCS[d['decl']](d['rad'], d['lema']) \
                if d['decl'] in ('2r', '3', '3i', '3n', '3ni') \
                else _DECL_FUNCS[d['decl']](d['rad'])
            # exceção gen. pl. (ex.: canis → canum já coberto por decl '3')
            out = f"**{d['lema'].upper()}** — {d['trad']}\n"
            out += f"{_DECL_LABEL[d['decl']]} | Substantivo {_GEN_LABEL[d['gen']]}\n\n"
            out += _render_tabela_decl(_GEN_LABEL[d['gen']].capitalize(), formas)
            return out

        # Adjetivo: TODOS os gêneros → uma tabela por gênero (instrução 1c)
        if chave in ADJETIVOS:
            a = ADJETIVOS[chave]
            rad = a['rad']
            out = f"**{a['lema'].upper()}** — {a['trad']}\n"
            if a['tipo'] in ('12', '12r'):
                out += "Adjetivo de 1ª/2ª declinação\n\n"
                nom_m = a['lema'] if a['tipo'] == '12r' else rad + 'us'
                out += _render_tabela_decl('Masculino', _decl_2us(rad, nom_m)) + "\n"
                out += _render_tabela_decl('Feminino',  _decl_1(rad)) + "\n"
                out += _render_tabela_decl('Neutro',    _decl_2n(rad))
            else:  # 3ª declinação, 2 terminações
                out += "Adjetivo de 3ª declinação (duas terminações)\n\n"
                out += _render_tabela_decl('Masculino', _decl_3adj_mf(rad, a['lema'])) + "\n"
                out += _render_tabela_decl('Feminino',  _decl_3adj_mf(rad, a['lema'])) + "\n"
                out += _render_tabela_decl('Neutro',    _decl_3adj_n(rad))
            return out

        # Verbo → não se declina; redireciona
        if chave in _VERBO_ALIASES:
            v = VERBOS[_VERBO_ALIASES[chave]]
            return (f"**{v['lema']}** é verbo ({_CONJ_LABEL[v['conj']]}) — não se "
                    f"declina. Para conjugar: conj {palavra}")

        # Não sabe → diz (instrução 1g)
        return (f"Não tenho os dados de declinação de '{palavra}' na minha base "
                f"do Familia Romana. Não vou inventar — confirme a grafia ou "
                f"peça a declinação diretamente no chat.")

    # ---------- conj ----------

    def _conjugar(self, verbo: str) -> str:
        chave = _strip_macrons(verbo)

        if chave not in _VERBO_ALIASES:
            if chave in SUBSTANTIVOS or chave in ADJETIVOS:
                return (f"'{verbo}' não é verbo — não se conjuga. "
                        f"Para declinar: decl {verbo}")
            return (f"Não tenho os dados de conjugação de '{verbo}' na minha "
                    f"base do Familia Romana. Não vou inventar.")

        v = VERBOS[_VERBO_ALIASES[chave]]
        out = f"**{v['lema'].upper()}** — {v['trad']}\n"
        out += f"{_CONJ_LABEL[v['conj']]}\n\n"
        out += _render_tabela_conj(v)
        return out

    # ---------- trad / sig ----------

    def _traduzir(self, palavra: str) -> str:
        chave = _strip_macrons(palavra)
        out = None

        if chave in SUBSTANTIVOS:
            d = SUBSTANTIVOS[chave]
            out = (f"**{d['lema']}** → {d['trad']}\n"
                   f"{_DECL_LABEL[d['decl']]} | Substantivo {_GEN_LABEL[d['gen']]}\n")
            lema = d['lema']
        elif chave in ADJETIVOS:
            a = ADJETIVOS[chave]
            tipo = ('1ª/2ª declinação' if a['tipo'] in ('12', '12r')
                    else '3ª declinação')
            out = (f"**{a['lema']}** → {a['trad']}\n"
                   f"Adjetivo de {tipo} (declina nos três gêneros)\n")
            lema = a['lema']
        elif chave in _VERBO_ALIASES:
            v = VERBOS[_VERBO_ALIASES[chave]]
            out = (f"**{v['lema']}** → {v['trad']}\n"
                   f"Verbo, {_CONJ_LABEL[v['conj']]}\n")
            lema = v['lema']
        else:
            return (f"Não tenho '{palavra}' na minha base do Familia Romana. "
                    f"Não vou inventar uma tradução.")

        exemplos = self._exemplos_do_livro(_strip_macrons(lema))
        if exemplos:
            out += "\nExemplos (Familia Romana):\n"
            for ex in exemplos:
                out += f"• {ex}\n"
        else:
            out += "\n(Exemplos do livro indisponíveis — familia_romana.db ausente na pasta ou sem ocorrências.)\n"
        return out

    # ---------- cor ----------

    def _corrigir(self, frase: str) -> str:
        """
        Honesto (instrução 1g): este script verifica apenas o VOCABULÁRIO
        contra a base do Familia Romana. Análise gramatical completa
        (casos, concordância, sintaxe) não é feita aqui — não invento correções.
        """
        palavras = re.findall(r"[A-Za-zĀĒĪŌŪȲāēīōūȳ]+", frase)
        if not palavras:
            return "Não identifiquei palavras na frase."

        reconhecidas, desconhecidas = [], []
        for p in palavras:
            chave = _strip_macrons(p)
            if (chave in SUBSTANTIVOS or chave in ADJETIVOS
                    or chave in _VERBO_ALIASES):
                reconhecidas.append(p)
                continue
            # tenta no banco completo (7.566 formas do livro)
            achou = self._db_lookup_contextos(chave) is not None
            (reconhecidas if achou else desconhecidas).append(p)

        out = f"Frase analisada: \"{frase}\"\n\n"
        out += "**O que está certo (vocabulário):** "
        out += (", ".join(reconhecidas) if reconhecidas
                else "nenhuma palavra reconhecida") + "\n"
        if desconhecidas:
            out += ("**O que pode estar errado:** palavras não encontradas no "
                    "Familia Romana: " + ", ".join(desconhecidas) + "\n")
        else:
            out += "**O que pode estar errado:** nenhum problema de vocabulário detectado.\n"
        out += ("\n**Versão consolidada:** este script só valida vocabulário; "
                "não analiso concordância, casos ou sintaxe — e não vou inventar "
                "uma correção. Para a correção gramatical completa, use o "
                "comando 'cor' diretamente no chat com o Claude.")
        return out

    def close(self):
        pass

# ============================================================================
# Interface pública
# ============================================================================

_processor: Optional[FamiliaRomanaProcessor] = None

def process_command(command: str) -> str:
    global _processor
    if _processor is None:
        _processor = FamiliaRomanaProcessor()
    try:
        return _processor.process_command(command)
    except Exception as e:
        return f"Erro: {e}"

# ============================================================================
# CLI — sem saudação, direto ao assunto (instrução 1)
# ============================================================================

def main():
    import sys
    # busybox-style: se invocado via symlink chamado decl/conj/trad/sig/cor,
    # o próprio nome do executável é o comando → "conj ponere" e pronto.
    prog = Path(sys.argv[0]).name.lower()
    if prog.endswith('.py'):
        prog = prog[:-3]
    if prog in ('decl', 'conj', 'trad', 'sig', 'cor'):
        print(process_command(' '.join([prog] + sys.argv[1:])))
        return
    # modo one-shot: fr decl puella
    if len(sys.argv) > 1:
        print(process_command(' '.join(sys.argv[1:])))
        return
    # modo interativo
    while True:
        try:
            comando = input("> ").strip()
        except (KeyboardInterrupt, EOFError):
            break
        if comando.lower() in ('exit', 'quit', 'sair'):
            break
        if comando:
            print(process_command(comando) + "\n")

if __name__ == '__main__':
    try:
        main()
    except BrokenPipeError:
        pass
