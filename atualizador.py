import json
import os
import subprocess
import sys
from typing import Optional, Tuple
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from config import URL_VERSAO_NUVEM

USER_AGENT = "Planilhador-Updater"

def _parse_versao(valor: str) -> Optional[Tuple[int, ...]]:
    try:
        partes = tuple(int(p) for p in valor.strip().split("."))
        return partes if partes else None
    except Exception:
        return None

def _url_https(url: str) -> bool:
    try:
        return urlparse(url).scheme.lower() == "https"
    except Exception:
        return False

def verificar_nova_versao(versao_atual: str) -> Optional[Tuple[str, str]]:
    if not _url_https(URL_VERSAO_NUVEM):
        return None

    req = Request(URL_VERSAO_NUVEM, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=5) as resposta:
            if resposta.status != 200:
                return None
            dados_nuvem = json.loads(resposta.read().decode("utf-8"))

        versao_nuvem = dados_nuvem.get("versao")
        url_download = dados_nuvem.get("url_download")

        if not isinstance(versao_nuvem, str) or not isinstance(url_download, str):
            return None

        if not _url_https(url_download):
            return None

        atual = _parse_versao(versao_atual)
        nuvem = _parse_versao(versao_nuvem)
        if not atual or not nuvem:
            return None

        if nuvem > atual:
            return versao_nuvem, url_download
    except Exception:
        return None

    return None

def baixar_e_aplicar_update(url_download: str) -> None:
    if not _url_https(url_download):
        raise RuntimeError("URL de update invalida")

    if not getattr(sys, "frozen", False):
        raise RuntimeError("Update in-place so e suportado no executavel empacotado")

    caminho_exe_atual = sys.executable
    pasta_atual = os.path.dirname(caminho_exe_atual)
    nome_exe_atual = os.path.basename(caminho_exe_atual)

    pid_atual = os.getpid()
    nome_exe_novo = f"novo_update_{pid_atual}.exe"
    caminho_exe_novo = os.path.join(pasta_atual, nome_exe_novo)

    req = Request(url_download, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=30) as resposta, open(caminho_exe_novo, "wb") as arquivo:
        while True:
            chunk = resposta.read(8192)
            if not chunk:
                break
            arquivo.write(chunk)

    if not os.path.exists(caminho_exe_novo) or os.path.getsize(caminho_exe_novo) < 1024:
        raise RuntimeError("Arquivo de update invalido")

    with open(caminho_exe_novo, "rb") as arquivo_exe:
        if arquivo_exe.read(2) != b"MZ":
            raise RuntimeError("Download nao parece ser um executavel valido")

    caminho_bat = os.path.join(pasta_atual, "atualizador.bat")
    caminho_log = os.path.join(pasta_atual, "atualizador.log")
    conteudo_bat = (
        "@echo off\n"
        "setlocal\n"
        f"set \"LOG={caminho_log}\"\n"
        "echo [%%date%% %%time%%] iniciando atualizador > \"%LOG%\"\n"
        f"cd /d \"{pasta_atual}\"\n"
        "echo [%%date%% %%time%%] aguardando processo antigo >> \"%LOG%\"\n"
        ":wait_proc\n"
        f"tasklist /FI \"PID eq {pid_atual}\" 2>NUL | find /I \"{pid_atual}\" >NUL\n"
        "if not errorlevel 1 (timeout /t 1 /nobreak >NUL & goto wait_proc)\n"
        "echo [%%date%% %%time%%] processo antigo finalizado >> \"%LOG%\"\n"
        ":swap\n"
        f"del /f /q \"{nome_exe_atual}\" >NUL 2>NUL\n"
        f"if exist \"{nome_exe_atual}\" (timeout /t 1 /nobreak >NUL & goto swap)\n"
        f"ren \"{nome_exe_novo}\" \"{nome_exe_atual}\" >NUL 2>NUL\n"
        "if errorlevel 1 (timeout /t 1 /nobreak >NUL & goto swap)\n"
        "echo [%%date%% %%time%%] troca de executavel concluida >> \"%LOG%\"\n"
        "set _MEIPASS=\n"
        "set _MEIPASS2=\n"
        f"start \"\" /D \"{pasta_atual}\" \"{caminho_exe_atual}\"\n"
        "echo [%%date%% %%time%%] comando de inicializacao enviado >> \"%LOG%\"\n"
        "del \"%~f0\" >NUL 2>NUL\n"
    )

    with open(caminho_bat, "w", encoding="utf-8") as arquivo:
        arquivo.write(conteudo_bat)

    env_limpo = os.environ.copy()
    chaves_para_remover = [k for k in env_limpo.keys() if k.upper().startswith("_MEI")]
    for k in chaves_para_remover:
        env_limpo.pop(k, None)

    if sys.platform == "win32":
        CREATE_NO_WINDOW = 0x08000000
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        DETACHED_PROCESS = 0x00000008
        creationflags = CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS
        subprocess.Popen(
            ["cmd.exe", "/d", "/c", f'call "{caminho_bat}"'],
            creationflags=creationflags,
            close_fds=True,
            cwd=pasta_atual,
            env=env_limpo,
        )
    else:
        subprocess.Popen(
            ["sh", caminho_bat],
            close_fds=True,
            cwd=pasta_atual,
            env=env_limpo,
        )

    os._exit(0)