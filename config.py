import json
import os
from typing import Any

VERSAO_ATUAL = "1.0.0"
URL_VERSAO_NUVEM = "https://raw.githubusercontent.com/JansemWall/Filtro-de-Planilha-Avan-ado/main/version.json"
VERIFICAR_ATUALIZACAO_AUTOMATICA = False

PASTA_SISTEMA = "_dados_sistema"
PASTA_ORIGENS = os.path.join(PASTA_SISTEMA, "origens")
PASTA_RESULTADOS = os.path.join(PASTA_SISTEMA, "resultados")
PASTA_COLUNAS_CACHE = os.path.join(PASTA_SISTEMA, "colunas_cache")
ARQUIVO_HISTORICO = os.path.join(PASTA_SISTEMA, "historico.json")
ARQUIVO_BASES = os.path.join(PASTA_SISTEMA, "bases.json")


def inicializar_sistema() -> None:
    for pasta in [PASTA_SISTEMA, PASTA_ORIGENS, PASTA_RESULTADOS, PASTA_COLUNAS_CACHE]:
        if not os.path.exists(pasta):
            os.makedirs(pasta)

    if not os.path.exists(ARQUIVO_HISTORICO):
        salvar_json(ARQUIVO_HISTORICO, [])

    if not os.path.exists(ARQUIVO_BASES):
        salvar_json(ARQUIVO_BASES, {})


def carregar_json(caminho: str, default: Any) -> Any:
    try:
        with open(caminho, "r", encoding="utf-8") as arquivo:
            return json.load(arquivo)
    except Exception:
        return default


def salvar_json(caminho: str, dados: Any) -> None:
    with open(caminho, "w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, indent=4, ensure_ascii=False)
