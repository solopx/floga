
# FLogA - Fortinet Log Analyzer

![Python](https://img.shields.io/badge/Python-3.x-blue.svg) ![Tkinter](https://img.shields.io/badge/GUI-Tkinter-green.svg) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## V2 is OUT NOW!

<img src="https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExYTZ1eHpkb3lvemdpZmZ6ejMxamR4ZXJrYTJsNGl2cDlneHdsdHYwYyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/yr7n0u3qzO9nG/giphy.gif" width=20% height=20%>

[Read this in English](README.en.md)

Um aplicativo de desktop simples e leve para visualização, análise e tratamento de logs de equipamentos Fortinet, desenvolvido em Python.

Este aplicativo torna mais fácil a análise e a gerência de logs de dispositivos UTM para usuários da área de redes e segurança sem a necessidade da utilização de um appliance FortiAnalyzer.

## Funcionalidades

- **Visualização gráfica de Logs**: Exibe de forma detalhada arquivos logs em formato `.log` ou `.txt` no formato `key=value`.
- **Busca dinâmica:** Filtra logs por qualquer termo em todos os campos, com busca case-insensitive.
- **Busca temporal:** Busca por intervalo de tempo (data/hora)
- **Análise Visual Simples:** Coloração automática para níveis e para ações comuns de tráfego.
- **Agrupamento de Registros:** Agrupe logs por qualquer coluna para visualizar totais por IP, ação, status, etc., com drill-down para filtrar pelos registros do grupo.
- **Plotagem de gráficos:** Gráficos com capacidade de exportação para melhor visualização e apresentação dos dados coletados.
- **Inspeção Detalhada:** Clique duplo em qualquer linha para abrir uma janela de detalhes com todos os campos do log selecionado.
- **Exportação de Dados**: Possibilidade de exportação dos dados selecionados em formatos .csv ou .json

## Screenshots

![Screenshot 0](/assets/screenshot-00.png)
![Screenshot 2](/assets/screenshot-02.png)

## Como Usar:

### Pré-requisitos:
Python 3.x

### Execução:

1.  **Baixe o Repositório**
    ```bash
    git clone https://github.com/solopx/floga.git
    ```
2.  **Acesse o diretório**
    ```
    cd floga
    ```
3.  **Instale as dependências**
    ```bash
    pip install -r requirements.txt
    ```    
4.  **Execute o Script**
    ```bash
    python src/main.py
    ```

## Utilizando a aplicação:

1. Carregar Logs: Clique no botão "Abrir Log" e selecione um arquivo de log (extensões .log ou .txt).
2. Busca Geral: Digite termos de pesquisa na barra de busca.
3. Filtragem por período: Selecione data/hora específicos e marque a checkbox **filtrar por período** para visualizar os logs do intervalo de tempo selecionado.
4. Clique com o botão direito sobre as linhas para exportar as linhas como texto.
5. Clique em "Exportar CSV" ou Exportar JSON" para exportar os resultados da busca para os formatos .csv ou .json.
6. Duplo clique sobre a linha do log abre uma janela com os dados completos da entrada de log.
7. Agrupar por: Clique em "Agrupar por" e selecione uma coluna para ver o total de registros por valor. Clique em uma linha do agrupamento para filtrar pelos registros daquele grupo. Clique em "Limpar" para desfazer o filtro do grupo ou "Voltar" para retornar à visualização completa.
8. Gráficos: Clique no menu Gráficos para gerar e exportar gráficos a partir dos logs filtrados.

## Estrutura dos Logs Esperada

O script analisa entrada de logs no formato `key=value`, como por exemplo:

`date=2023-10-27 time=10:30:00 logid=0000000000 type=traffic subtype=forward srcip=192.168.1.10 srcport=54321 srcintf="port1" dstip=8.8.8.8 dstport=53 dstintf="wan1" policyid=1 action=accept service="dns" utmaction=passthrough sentbyte=123 rcvdbyte=456`

## Estrutura da aplicação

A aplicação foi dividida em 4 arquivos para melhor manutenção e expansão:

1. **log_engine.py:** Motor de parse de logs, busca e filtros
2. **ui.py:** Interface gráfica em Tkinter.
3. **charts.py:** Geração e exibição de gráficos.
4. **main.py:** Start da aplicação.


## Contribuições

Contribuições são bem-vindas! Se você tiver ideias para melhorias, sinta-se à vontade para abrir uma *issue* ou enviar um *pull request*.

## Licença

Este projeto está licenciado sob a Licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

---
Desenvolvido por solopx
GitHub: [https://github.com/solopx/](https://github.com/solopx/)
