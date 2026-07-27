"""Handler da AWS Lambda: roda a exportação diária do DJEN e envia e-mail/WhatsApp.

Reaproveita djen.py e notificacao.py sem alterações (ambos usam só a biblioteca
padrão do Python). A configuração vem inteiramente de variáveis de ambiente da
função Lambda — não há config.json nem arquivos de segredo no pacote, já que o
filesystem da Lambda é efêmero.

Disparado pelo EventBridge Scheduler (veja deploy.sh) todo dia às 5:59, no
fuso America/Sao_Paulo, com a função hospedada na região sa-east-1 (São Paulo)
para que a chamada à API do CNJ saia por um IP brasileiro.
"""

import json
import os
from pathlib import Path

import djen
import notificacao


def _lista(env_var: str) -> list:
    bruto = os.environ.get(env_var, "")
    return [e.strip() for e in bruto.split(",") if e.strip()]


def _config_email() -> dict:
    return {
        "habilitado": os.environ.get("EMAIL_HABILITADO", "true").lower() == "true",
        "provedor": os.environ.get("EMAIL_PROVEDOR", "sendgrid"),
        "para": _lista("EMAIL_PARA"),
        "de": os.environ.get("EMAIL_DE", ""),
        "de_nome": os.environ.get("EMAIL_DE_NOME", ""),
        "smtp_host": os.environ.get("SMTP_HOST", "smtp.mail.me.com"),
        "smtp_porta": int(os.environ.get("SMTP_PORTA", "587")),
        "smtp_usuario": os.environ.get("SMTP_USUARIO", ""),
        "enviar_quando_vazio": os.environ.get("ENVIAR_QUANDO_VAZIO", "true").lower() == "true",
    }


def _config_whatsapp() -> dict:
    return {
        "habilitado": os.environ.get("WHATSAPP_HABILITADO", "false").lower() == "true",
        "de": os.environ.get("WHATSAPP_DE", ""),
        "para": _lista("WHATSAPP_PARA"),
        "enviar_quando_vazio": os.environ.get("WHATSAPP_ENVIAR_QUANDO_VAZIO", "false").lower() == "true",
    }


def handler(event, context):
    numero_oab = os.environ["NUMERO_OAB"]
    uf_oab = os.environ.get("UF_OAB", "SP")
    nome_adv = os.environ.get("NOME_ADVOGADO", "")
    sigla_tribunal = os.environ.get("SIGLA_TRIBUNAL", "")

    data = (event or {}).get("data") or djen.hoje_brasilia().isoformat()
    itens, total = djen.buscar_comunicacoes(
        numero_oab=numero_oab, uf_oab=uf_oab,
        data_inicio=data, data_fim=data, sigla_tribunal=sigla_tribunal)

    titulo = (f"{nome_adv} — " if nome_adv else "") + f"DJEN OAB {numero_oab}/{uf_oab} — {data}"
    corpo_html = djen.gerar_html(itens, titulo,
                                 f"{len(itens)} publicação(ões) disponibilizada(s) em {data}")
    corpo_csv = djen.gerar_csv(itens)
    resumo = djen.resumo_texto(itens, numero_oab, uf_oab, data, data)

    resultado = {"data": data, "total": total, "coletadas": len(itens),
                 "email_enviado": False, "whatsapp_enviado": 0}

    cfg_email = _config_email()
    if cfg_email["habilitado"] and (itens or cfg_email["enviar_quando_vazio"]):
        assunto = f"DJEN OAB {numero_oab}/{uf_oab} — {len(itens)} publicação(ões) em {data}"
        # notificacao.enviar espera caminhos de arquivo para os anexos; a Lambda
        # não tem disco persistente, então gravamos em /tmp (efêmero, apagado
        # após a invocação — não precisamos manter histórico aqui).
        caminho_csv = f"/tmp/djen_{data}.csv"
        caminho_html = f"/tmp/djen_{data}.html"
        with open(caminho_csv, "w", encoding="utf-8") as f:
            f.write(corpo_csv)
        with open(caminho_html, "w", encoding="utf-8") as f:
            f.write(corpo_html)
        notificacao.enviar(cfg_email, assunto, resumo, corpo_html,
                           [Path(caminho_csv), Path(caminho_html)])
        resultado["email_enviado"] = True

    cfg_wpp = _config_whatsapp()
    if cfg_wpp["habilitado"] and cfg_wpp["para"] and (itens or cfg_wpp["enviar_quando_vazio"]):
        texto = (f"DJEN OAB {numero_oab}/{uf_oab}: {len(itens)} publicação(ões) "
                 f"em {data}. Detalhes no e-mail.")
        resultado["whatsapp_enviado"] = notificacao.enviar_whatsapp(cfg_wpp, texto)

    print(json.dumps(resultado, ensure_ascii=False))
    return resultado
