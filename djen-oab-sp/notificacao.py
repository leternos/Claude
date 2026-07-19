"""Envio de e-mail com backend selecionável: SMTP ou SendGrid (Twilio).

Sem dependências externas — SMTP via smtplib, SendGrid via HTTP (urllib).
O provedor é escolhido em config.json → email.provedor ("smtp" | "sendgrid").

Credenciais (nunca ficam no config.json):
  SMTP     → variável DJEN_SMTP_SENHA        ou arquivo .smtp_senha
  SendGrid → variável SENDGRID_API_KEY       ou arquivo .sendgrid_key
"""

import base64
import json
import os
import smtplib
import urllib.parse
import urllib.request
from email.message import EmailMessage
from pathlib import Path

RAIZ = Path(__file__).resolve().parent


def _segredo(variaveis, arquivo) -> str:
    for nome in variaveis:
        valor = os.environ.get(nome)
        if valor:
            return valor.strip()
    caminho = RAIZ / arquivo
    if caminho.exists():
        return caminho.read_text(encoding="utf-8").strip()
    return ""


def _anexo(caminho: Path) -> dict:
    tipos = {"csv": "text/csv", "html": "text/html", "json": "application/json"}
    return {
        "nome": caminho.name,
        "tipo": tipos.get(caminho.suffix.lstrip("."), "application/octet-stream"),
        "bytes": caminho.read_bytes(),
    }


def enviar(cfg_email: dict, assunto: str, corpo_txt: str, corpo_html: str,
           caminhos_anexos: list):
    """Despacha o e-mail pelo provedor configurado."""
    anexos = [_anexo(Path(c)) for c in caminhos_anexos]
    provedor = (cfg_email.get("provedor") or "smtp").lower()
    if provedor == "sendgrid":
        _enviar_sendgrid(cfg_email, assunto, corpo_txt, corpo_html, anexos)
    elif provedor == "smtp":
        _enviar_smtp(cfg_email, assunto, corpo_txt, corpo_html, anexos)
    else:
        raise SystemExit(f"Provedor de e-mail desconhecido: {provedor!r} "
                         "(use 'smtp' ou 'sendgrid' em config.json).")


# ---------------------------------------------------------------- SMTP --------
def _enviar_smtp(cfg, assunto, corpo_txt, corpo_html, anexos):
    senha = _segredo(("DJEN_SMTP_SENHA", "DJEN_SMTP_PASSWORD"), ".smtp_senha")
    if not senha:
        raise SystemExit("Defina DJEN_SMTP_SENHA (ou o arquivo .smtp_senha) com a senha "
                         "de aplicativo do SMTP, ou rode com --sem-email.")
    msg = EmailMessage()
    msg["Subject"] = assunto
    msg["From"] = cfg["de"]
    msg["To"] = ", ".join(cfg["para"])
    msg.set_content(corpo_txt)
    if corpo_html:
        msg.add_alternative(corpo_html, subtype="html")
    for a in anexos:
        maintype, _, subtype = a["tipo"].partition("/")
        msg.add_attachment(a["bytes"], maintype=maintype, subtype=subtype,
                           filename=a["nome"])
    with smtplib.SMTP(cfg["smtp_host"], int(cfg.get("smtp_porta", 587)),
                      timeout=60) as smtp:
        smtp.starttls()
        smtp.login(cfg.get("smtp_usuario") or cfg["de"], senha)
        smtp.send_message(msg)


# ------------------------------------------------------------ SendGrid --------
SENDGRID_URL = "https://api.sendgrid.com/v3/mail/send"


def montar_payload_sendgrid(cfg, assunto, corpo_txt, corpo_html, anexos) -> dict:
    """Monta o corpo JSON da API do SendGrid (função pura, testável sem rede)."""
    conteudo = [{"type": "text/plain", "value": corpo_txt or " "}]
    if corpo_html:
        conteudo.append({"type": "text/html", "value": corpo_html})
    payload = {
        "personalizations": [{"to": [{"email": e} for e in cfg["para"]]}],
        "from": {"email": cfg["de"], "name": cfg.get("de_nome", "DJEN OAB")},
        "subject": assunto,
        "content": conteudo,
    }
    if anexos:
        payload["attachments"] = [{
            "content": base64.b64encode(a["bytes"]).decode("ascii"),
            "type": a["tipo"],
            "filename": a["nome"],
            "disposition": "attachment",
        } for a in anexos]
    return payload


def _enviar_sendgrid(cfg, assunto, corpo_txt, corpo_html, anexos):
    chave = _segredo(("SENDGRID_API_KEY", "DJEN_SENDGRID_KEY"), ".sendgrid_key")
    if not chave:
        raise SystemExit("Defina SENDGRID_API_KEY (ou o arquivo .sendgrid_key) com a "
                         "API key do SendGrid, ou rode com --sem-email.")
    payload = montar_payload_sendgrid(cfg, assunto, corpo_txt, corpo_html, anexos)
    req = urllib.request.Request(
        SENDGRID_URL, data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {chave}",
                 "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as resp:
        if resp.status not in (200, 202):
            raise SystemExit(f"SendGrid respondeu HTTP {resp.status}: {resp.read()[:300]}")


# ------------------------------------------------------ WhatsApp (Twilio) -----
TWILIO_URL = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"


def montar_form_twilio(de: str, para: str, texto: str) -> dict:
    """Campos do formulário da API de mensagens do Twilio (função pura, testável)."""
    return {"From": de, "To": para, "Body": texto}


def enviar_whatsapp(cfg_wpp: dict, texto: str) -> int:
    """Envia uma mensagem de WhatsApp por número em cfg_wpp['para']. Retorna quantos."""
    sid = _segredo(("TWILIO_ACCOUNT_SID", "DJEN_TWILIO_SID"), ".twilio_sid")
    token = _segredo(("TWILIO_AUTH_TOKEN", "DJEN_TWILIO_TOKEN"), ".twilio_token")
    if not sid or not token:
        raise SystemExit("Defina TWILIO_ACCOUNT_SID e TWILIO_AUTH_TOKEN (ou os arquivos "
                         ".twilio_sid / .twilio_token) para enviar WhatsApp.")
    url = TWILIO_URL.format(sid=sid)
    auth = base64.b64encode(f"{sid}:{token}".encode("utf-8")).decode("ascii")
    enviados = 0
    for para in cfg_wpp["para"]:
        dados = urllib.parse.urlencode(
            montar_form_twilio(cfg_wpp["de"], para, texto)).encode("utf-8")
        req = urllib.request.Request(
            url, data=dados, method="POST",
            headers={"Authorization": f"Basic {auth}",
                     "Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            if resp.status not in (200, 201):
                raise SystemExit(f"Twilio respondeu HTTP {resp.status}: {resp.read()[:300]}")
        enviados += 1
    return enviados
