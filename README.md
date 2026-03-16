# ExcellKiller

Aplicativo desktop em Python (CustomTkinter) para filtrar planilhas grandes com regras em funil e salvar o resultado em Excel.

## O que ele faz

- Carrega base CSV, XLSX ou XLS
- Permite criar multiplas regras de busca (AND entre regras)
- Aceita lista de termos colada do Excel (virgula, ponto e virgula ou quebra de linha)
- Processa arquivos em lotes para aguentar bases grandes
- Salva historico das execucoes
- Permite exportar novamente resultados antigos
- Exibe botao de abrir planilha quando o arquivo exportado existe no disco

## Tecnologias

- Python 3.13+
- CustomTkinter
- Pandas
- OpenPyXL (exportacao para .xlsx)

## Estrutura do projeto

- `app.py`: aplicacao principal (UI + processamento)
- `_dados_sistema/origens`: copias imutaveis das bases
- `_dados_sistema/resultados`: resultados filtrados em CSV
- `_dados_sistema/historico.json`: historico de buscas e exportacoes
- `_dados_sistema/bases.json`: bases salvas para reutilizacao

## Como rodar

1. Criar ambiente virtual (se ainda nao existir)
2. Ativar ambiente
3. Instalar dependencias
4. Executar o app

### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install customtkinter pandas openpyxl
python app.py
```

## Como usar

1. Selecione a base de dados
2. Adicione uma ou mais regras de busca
3. Clique em "Pesquisar e Gerar Resultado"
4. Escolha onde salvar o Excel final
5. Consulte a aba "Historico de Resultados" para reexportar ou abrir planilhas ja exportadas

## Regras de filtro

- Cada bloco de regra representa um filtro
- O resultado final respeita o encadeamento das regras (funil)
- Em cada regra:
  - Colunas: informe uma ou varias colunas separadas por virgula
  - Termos: informe um ou varios termos separados por virgula, ponto e virgula ou quebra de linha

## Observacoes importantes

- Na primeira importacao de um arquivo externo, o sistema cria uma copia no cofre local (`_dados_sistema/origens`)
- Para arquivos muito grandes, o processamento ocorre em chunks para reduzir consumo de memoria
- Se um arquivo exportado for movido ou excluido, o botao "Abrir Planilha" deixa de aparecer para aquele registro

## Build (opcional)

Existe um `app.spec` no projeto para gerar executavel com PyInstaller.

Exemplo:

```powershell
pip install pyinstaller
pyinstaller app.spec
```
