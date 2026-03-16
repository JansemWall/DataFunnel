import os
import shutil
from datetime import datetime
from threading import Event
from typing import Callable, Optional

import pandas as pd

from config import (
    ARQUIVO_BASES,
    ARQUIVO_HISTORICO,
    PASTA_ORIGENS,
    PASTA_RESULTADOS,
    carregar_json,
    salvar_json,
)

StatusCallback = Optional[Callable[[str], None]]


def carregar_bases() -> dict[str, str]:
    return carregar_json(ARQUIVO_BASES, {})


def salvar_bases(bases: dict[str, str]) -> None:
    salvar_json(ARQUIVO_BASES, bases)


def carregar_historico() -> list[dict]:
    return carregar_json(ARQUIVO_HISTORICO, [])


def salvar_historico(historico: list[dict]) -> None:
    salvar_json(ARQUIVO_HISTORICO, historico)


def salvar_nova_base(
    bases_salvas: dict[str, str], nome_arquivo: str, caminho_imutavel: str
) -> tuple[dict[str, str], str]:
    base_nome = nome_arquivo
    contador = 1

    while base_nome in bases_salvas and bases_salvas[base_nome] != caminho_imutavel:
        base_nome = f"{nome_arquivo} ({contador})"
        contador += 1

    bases_salvas[base_nome] = caminho_imutavel
    salvar_bases(bases_salvas)
    return bases_salvas, base_nome


def preparar_base(
    caminho_base_ativa: str,
    is_base_no_cofre: bool,
    bases_salvas: dict[str, str],
    timestamp: str,
    status_callback: StatusCallback = None,
) -> tuple[str, str, bool, dict[str, str]]:
    if is_base_no_cofre:
        caminho_origem_imutavel = caminho_base_ativa
        nome_original = os.path.basename(caminho_origem_imutavel)
        if status_callback:
            status_callback("Lendo base do cache local...")
        return caminho_origem_imutavel, nome_original, True, bases_salvas

    nome_original = os.path.basename(caminho_base_ativa)
    caminho_origem_imutavel = os.path.join(PASTA_ORIGENS, f"origem_{timestamp}.csv")

    if caminho_base_ativa.endswith((".xlsx", ".xls")):
        if status_callback:
            status_callback("Importando Excel para o cofre (isso demora apenas na 1a vez)...")
        df_temp = pd.read_excel(caminho_base_ativa)
        df_temp.to_csv(caminho_origem_imutavel, index=False, encoding="utf-8")
        del df_temp
    else:
        if status_callback:
            status_callback("Armazenando CSV no cofre...")
        shutil.copy2(caminho_base_ativa, caminho_origem_imutavel)

    bases_salvas, _ = salvar_nova_base(bases_salvas, nome_original, caminho_origem_imutavel)
    return caminho_origem_imutavel, nome_original, True, bases_salvas


def _iterador_csv(caminho_origem_imutavel: str, tamanho_lote: int):
    try:
        return pd.read_csv(
            caminho_origem_imutavel,
            encoding="utf-8",
            chunksize=tamanho_lote,
            low_memory=False,
        )
    except UnicodeDecodeError:
        return pd.read_csv(
            caminho_origem_imutavel,
            encoding="latin1",
            sep=";",
            chunksize=tamanho_lote,
            low_memory=False,
        )


def _cabecalho_csv(caminho_origem_imutavel: str) -> pd.Index:
    try:
        return pd.read_csv(caminho_origem_imutavel, nrows=0, encoding="utf-8").columns
    except UnicodeDecodeError:
        return pd.read_csv(caminho_origem_imutavel, nrows=0, encoding="latin1", sep=";").columns


def filtrar_em_lotes(
    caminho_origem_imutavel: str,
    regras_de_busca: list[dict[str, str]],
    tamanho_lote: int = 50000,
    stop_event: Optional[Event] = None,
    status_callback: StatusCallback = None,
) -> pd.DataFrame:
    resultados: list[pd.DataFrame] = []
    linhas_processadas = 0

    iterador = _iterador_csv(caminho_origem_imutavel, tamanho_lote)

    for chunk in iterador:
        if stop_event and stop_event.is_set():
            raise RuntimeError("PROCESSAMENTO_CANCELADO")

        linhas_processadas += len(chunk)
        if status_callback:
            status_callback(f"Aplicando funil de filtros... ({linhas_processadas} linhas)")

        chunk_filtrado = chunk

        for regra in regras_de_busca:
            if stop_event and stop_event.is_set():
                raise RuntimeError("PROCESSAMENTO_CANCELADO")

            if chunk_filtrado.empty:
                break

            termos_lista = [t.strip() for t in regra["termos"].split(",") if t.strip()]
            padrao_busca = "|".join(termos_lista)

            if regra["colunas"]:
                colunas_alvo = [c.strip() for c in regra["colunas"].split(",") if c.strip()]
                colunas_alvo = [c for c in colunas_alvo if c in chunk_filtrado.columns]

                if colunas_alvo:
                    mascara = (
                        chunk_filtrado[colunas_alvo]
                        .astype(str)
                        .apply(lambda col: col.str.contains(padrao_busca, case=False, na=False))
                        .any(axis=1)
                    )
                else:
                    mascara = pd.Series(False, index=chunk_filtrado.index)
            else:
                mascara = (
                    chunk_filtrado.astype(str)
                    .apply(lambda col: col.str.contains(padrao_busca, case=False, na=False))
                    .any(axis=1)
                )

            chunk_filtrado = chunk_filtrado[mascara]

        if not chunk_filtrado.empty:
            resultados.append(chunk_filtrado)

    if resultados:
        return pd.concat(resultados)

    return pd.DataFrame(columns=_cabecalho_csv(caminho_origem_imutavel))


def salvar_resultado_csv(df_filtrado: pd.DataFrame, timestamp: str) -> str:
    caminho_resultado_imutavel = os.path.join(PASTA_RESULTADOS, f"resultado_{timestamp}.csv")
    df_filtrado.to_csv(caminho_resultado_imutavel, index=False, encoding="utf-8")
    return caminho_resultado_imutavel


def exportar_dataframe_excel(df: pd.DataFrame, caminho_exportacao: str) -> None:
    df.to_excel(caminho_exportacao, index=False)


def gerar_nome_exportacao(regras_de_busca: list[dict[str, str]], timestamp: str) -> str:
    primeiro_termo = regras_de_busca[0]["termos"].split(",")[0].strip()[:15]
    return f"Exportacao_Busca_{primeiro_termo}_{timestamp}.xlsx"


def gerar_nome_recuperacao(timestamp: Optional[str] = None) -> str:
    ts = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"Recuperacao_Historico_{ts}.xlsx"


def formatar_regras_log(regras_de_busca: list[dict[str, str]]) -> str:
    return " -> ".join([f"[{r['colunas'] or 'Todas'}]=({r['termos']})" for r in regras_de_busca])


def registrar_execucao_historico(
    timestamp: str,
    data_hora_formatada: str,
    nome_original: str,
    caminho_origem_imutavel: str,
    caminho_resultado_imutavel: str,
    caminho_exportacao: str,
    regras_de_busca: list[dict[str, str]],
    qtd_linhas: int,
) -> None:
    historico = carregar_historico()

    registro = {
        "id": timestamp,
        "data_hora": data_hora_formatada,
        "arquivo_original": nome_original,
        "caminho_origem_imutavel": caminho_origem_imutavel,
        "caminho_resultado_imutavel": caminho_resultado_imutavel,
        "caminho_exportacao": caminho_exportacao,
        "termos": formatar_regras_log(regras_de_busca),
        "linhas": qtd_linhas,
        "regras_raw": regras_de_busca,
    }

    historico.insert(0, registro)
    salvar_historico(historico)


def atualizar_caminho_exportacao_historico(registro_id: str, novo_caminho: str) -> None:
    historico = carregar_historico()

    for item in historico:
        if item.get("id") == registro_id:
            item["caminho_exportacao"] = novo_caminho
            break

    salvar_historico(historico)


def exportar_resultado_historico(caminho_resultado_imutavel: str, caminho_salvar: str) -> None:
    df = pd.read_csv(caminho_resultado_imutavel, encoding="utf-8")
    df.to_excel(caminho_salvar, index=False)
