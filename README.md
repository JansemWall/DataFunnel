# Filtradorzera de planilhas

O ExcellKiller foi criado para acelerar a busca de informacoes em planilhas grandes, com uma operacao simples e foco em produtividade.

## Para que serve

- Encontrar rapidamente registros em arquivos CSV e Excel
- Aplicar filtros por colunas e termos de busca
- Reduzir trabalho manual de procurar linha por linha
- Gerar planilhas finais prontas para compartilhamento

## Beneficios para sua equipe

- Menos tempo gasto com consultas repetitivas
- Mais padrao no processo de filtragem
- Historico de pesquisas para reutilizacao
- Reexportacao facil de resultados anteriores

## Como usar (passo a passo)

1. Abra o sistema.
2. Selecione a base de dados (CSV, XLSX ou XLS).
3. Informe as regras de busca:
  - Colunas onde deseja procurar
  - Termos que devem ser encontrados
4. Clique em Pesquisar e Gerar Resultado.
5. Escolha onde salvar o arquivo final em Excel.
6. Consulte a aba Historico de Resultados para:
  - Exportar novamente
  - Abrir planilhas ja exportadas

## Regras de busca

- Voce pode adicionar varias regras na mesma pesquisa.
- Os termos podem ser colados em bloco (com virgula, ponto e virgula ou quebra de linha).
- O sistema aplica as regras em funil para chegar no resultado final.

## Historico e rastreabilidade

- Cada pesquisa fica registrada com data, base utilizada, regras aplicadas e quantidade de linhas encontradas.
- Quando voce exporta novamente um resultado, o caminho do novo arquivo fica salvo no historico.
- Se o arquivo for movido ou excluido, o botao Abrir Planilha deixa de aparecer automaticamente.

## Requisitos

- Sistema operacional Windows
- Microsoft Excel ou aplicativo compativel para abrir arquivos .xlsx

## Suporte

Em caso de erro ou duvida de uso, compartilhe:

- Captura de tela da mensagem apresentada
- Passos realizados antes do erro
- Nome do arquivo/base utilizada

Com essas informacoes, o atendimento fica mais rapido e assertivo.

---


## Stack

- Python 3.13+
- CustomTkinter
- Pandas
- OpenPyXL

## Estrutura do projeto

- app.py: aplicacao principal (interface + processamento)
- app.spec: configuracao de build com PyInstaller
- _dados_sistema/origens: copias imutaveis das bases importadas
- _dados_sistema/resultados: resultados filtrados em CSV
- _dados_sistema/historico.json: historico de execucoes e exportacoes
- _dados_sistema/bases.json: mapeamento de bases salvas

## Setup rapido (Windows / PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install customtkinter pandas openpyxl
python app.py
```

## Notas de implementacao

- Processamento em chunks para reduzir consumo de memoria em arquivos grandes.
- Exportacao e reexportacao atualizam caminho de arquivo no historico.
- Se a abertura da planilha falhar, o caminho salvo e limpo para ocultar automaticamente a opcao de abrir.

## Build executavel (opcional)

```powershell
pip install pyinstaller
pyinstaller app.spec
```
