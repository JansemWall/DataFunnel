# DataFunnel (Filtro e Conversor Avançado de Dados)

O **DataFunnel** é uma aplicação desktop de alta performance desenvolvida para resolver um dos maiores gargalos da manipulação de dados: lidar com planilhas gigantescas sem travar o computador. 

Originalmente criado como um poderoso mecanismo de busca recursiva (filtros em funil), o sistema evoluiu e agora também oferece a opção de **conversão direta e otimizada de arquivos Excel pesados para CSV**.

## Principais Funcionalidades

* **Filtros em Funil (Drill-down):** Aplique múltiplas regras de busca em sequência (lógica AND) ou pesquise vários termos na mesma regra (lógica OR). O limite é a sua necessidade.
* **Conversão Direta (Excel para CSV):** Extraia dados de arquivos `.xlsx` pesados de forma rápida e segura para o formato universal `.csv`.
* **Histórico e Reutilização:** O sistema memoriza suas buscas. Com um clique, você pode recarregar as regras exatas de uma pesquisa feita dias atrás e exportar novamente os resultados.
* **Auto-Update Nativo:** O sistema verifica atualizações via GitHub e se auto-atualiza de forma transparente e silenciosa.

## O Grande Diferencial: Engenharia e Otimização

O que torna o DataFunnel especial não é apenas o que ele faz, mas **como** ele faz. O sistema foi desenhado visando o mínimo consumo de hardware e a máxima produtividade:

* **Processamento em Chunks (Lotes):** Em vez de tentar carregar uma planilha de 1 milhão de linhas na memória RAM (o que causaria travamentos), o motor de dados lê e processa o arquivo em lotes (ex: 50.000 linhas por vez). Isso mantém o uso de memória baixíssimo e constante, não importa o tamanho do arquivo.
* **Arquitetura Multithreading:** A interface gráfica (UI) e o motor de dados rodam em pistas separadas. O processamento pesado acontece em *background*, garantindo que a tela nunca congele e permitindo o cancelamento de tarefas a qualquer momento.
* **Cofre de Dados (Cache Inteligente):** Ler arquivos Excel é um processo naturalmente lento. Para resolver isso, ao carregar um `.xlsx` pela primeira vez, o sistema cria uma cópia imutável em `.csv` no "Cofre do Sistema". Nas consultas seguintes, a base é carregada de forma quase instantânea.
* **Gestão de Resultados:** Todos os resultados filtrados são preservados fisicamente. Isso poupa o usuário de ter que rodar algoritmos pesados novamente caso precise apenas re-exportar uma base para um colega.

## Tecnologias Utilizadas

* **Python 3**
* **Pandas:** Motor principal para manipulação de DataFrames e leitura otimizada.
* **CustomTkinter:** Para uma interface gráfica moderna, responsiva e com suporte a *Dark Mode*.
* **Urllib / Subprocess:** Gerenciamento nativo de rede e do sistema operacional para o fluxo de auto-atualização.

## Download

O DataFunnel é distribuído como um arquivo executável `.exe` para Windows. Você pode baixá-lo diretamente do nosso repositório no GitHub:
[DataFunnel no GitHub](https://github.com/JansemWall/Filtro-de-Planilha-Avan-ado/releases)

## Como Usar (Para Desenvolvedores)

1. Clone o repositório.
2. Instale as dependências:
   ```bash
   pip install pandas customtkinter openpyxl