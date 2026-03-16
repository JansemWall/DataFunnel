import json
import os
import subprocess
import sys
from typing import Optional, Tuple
from urllib.request import Request, urlopen

from config import URL_VERSAO_NUVEM


def verificar_nova_versao(versao_atual: str) -> Optional[Tuple[str, str]]:
    req = Request(URL_VERSAO_NUVEM, headers={"User-Agent": "ExcellKiller-Updater"})
    with urlopen(req, timeout=5) as resposta:
        if resposta.status != 200:
            return None
        dados_nuvem = json.loads(resposta.read().decode("utf-8"))

    versao_nuvem = dados_nuvem.get("versao")
    url_download = dados_nuvem.get("url_download")

    if versao_nuvem and url_download and versao_nuvem != versao_atual:
        return versao_nuvem, url_download

    return None


def baixar_e_aplicar_update(url_download: str) -> None:
    caminho_exe_atual = sys.executable
    pasta_atual = os.path.dirname(caminho_exe_atual)
    nome_exe_atual = os.path.basename(caminho_exe_atual)

    caminho_exe_novo = os.path.join(pasta_atual, "novo_update_temp.exe")

    req = Request(url_download, headers={"User-Agent": "ExcellKiller-Updater"})
    with urlopen(req, timeout=30) as resposta, open(caminho_exe_novo, "wb") as arquivo:
        while True:
            chunk = resposta.read(8192)
            if not chunk:
                break
            arquivo.write(chunk)

    caminho_bat = os.path.join(pasta_atual, "atualizador.bat")
    conteudo_bat = (
        "@echo off\n"
        "echo Atualizando o sistema... aguarde um momento.\n"
        "timeout /t 2 /nobreak > NUL\n"
        f"del \"{caminho_exe_atual}\"\n"
        f"ren \"{caminho_exe_novo}\" \"{nome_exe_atual}\"\n"
        f"start \"\" \"{caminho_exe_atual}\"\n"
        "del \"%~f0\"\n"
    )

    with open(caminho_bat, "w", encoding="utf-8") as arquivo:
        arquivo.write(conteudo_bat)

    creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    subprocess.Popen([caminho_bat], creationflags=creationflags)

    os._exit(0)
