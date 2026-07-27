"""API simulada do DJEN para testes locais (o CDN real bloqueia IPs fora do Brasil).

Emula GET /api/v1/comunicacao com paginação e o formato de resposta real.
"""

import json
import os
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

OAB_ESPERADA = os.environ.get("DJEN_MOCK_OAB", "123456")

TEXTO = ("<p>Vistos. Intime-se a parte autora, por seu advogado, para manifestação "
         "no prazo de 15 (quinze) dias, nos termos do art. 350 do CPC.</p>")


def gerar_itens(n=130, data="2026-07-17"):
    itens = []
    for i in range(1, n + 1):
        itens.append({
            "id": i,
            "hash": f"hash-{i}",
            "data_disponibilizacao": data,
            "siglaTribunal": "TJSP" if i % 3 else "TRT2",
            "tipoComunicacao": "Intimação" if i % 2 else "Citação",
            "tipoDocumento": "Despacho",
            "nomeOrgao": f"{i}ª Vara Cível de São Paulo",
            "numero_processo": f"{i:07d}2020268260100",
            "numeroprocessocommascara": f"{i:07d}-20.2026.8.26.0100",
            "nomeClasse": "Procedimento Comum Cível",
            "link": f"https://comunica.pje.jus.br/consulta?id={i}",
            "texto": TEXTO,
            "destinatarios": [{"nome": f"Parte Autora {i}", "polo": "A"}],
            "destinatarioadvogados": [{
                "id": i, "comunicacao_id": i, "advogado_id": 1,
                "advogado": {"id": 1, "nome": "ADVOGADO TESTE",
                             "numero_oab": OAB_ESPERADA, "uf_oab": "SP"},
            }],
        })
    return itens


class MockHandler(BaseHTTPRequestHandler):
    itens = gerar_itens()

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(url.query)
        if url.path != "/api/v1/comunicacao":
            self.send_error(404)
            return
        if q.get("numeroOab", [""])[0] != OAB_ESPERADA:
            filtrados = []
        else:
            filtrados = self.itens
        pagina = int(q.get("pagina", ["1"])[0])
        por_pagina = int(q.get("itensPorPagina", ["100"])[0])
        inicio = (pagina - 1) * por_pagina
        corpo = json.dumps({
            "status": "success",
            "message": "Comunicações listadas com sucesso",
            "count": len(filtrados),
            "items": filtrados[inicio:inicio + por_pagina],
        }).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def log_message(self, *args):
        pass


def iniciar(porta=0):
    servidor = ThreadingHTTPServer(("127.0.0.1", porta), MockHandler)
    return servidor


if __name__ == "__main__":
    s = iniciar(8860)
    print(f"Mock DJEN em http://127.0.0.1:{s.server_address[1]}")
    s.serve_forever()
