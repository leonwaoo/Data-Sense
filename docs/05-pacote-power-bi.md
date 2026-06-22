# Pacote Power BI

## Objetivo

O pacote Power BI permite que o usuario baixe os dados ja analisados pelo DataSense e leve a leitura gerencial para o Power BI com menos trabalho manual.

Ele foi criado para apoiar gestores e analistas que querem montar um painel executivo com:

- dados tratados;
- comparativo mensal;
- insights gerenciais;
- sugestoes de graficos;
- orientacao de medidas e layout.

## Como gerar

Depois de carregar um arquivo no DataSense, use o botao de exportacao para Power BI na interface.

A API tambem disponibiliza o pacote pelo endpoint:

```text
GET /datasets/{dataset_id}/powerbi.zip
```

## Arquivos do pacote

O arquivo `.zip` gerado contem:

- `dados_tratados.csv`: base tabular pronta para importar no Power BI.
- `comparativo_mensal.csv`: metricas por periodo, com variacao absoluta, variacao percentual, media movel, acumulado do ano, comparacao com o ano anterior e comparacao dos ultimos 3 meses.
- `insights_gerenciais.csv`: principais insights, alertas e recomendacoes calculados pelo DataSense.
- `graficos_sugeridos.csv`: lista de visuais recomendados, com tipo de grafico, eixo, metrica e objetivo.
- `metadados.json`: mapeamento de colunas, dominio detectado, metricas principais e contexto da analise.
- `README.txt`: guia rapido para importar e montar o relatorio no Power BI.

## Uso recomendado no Power BI

1. Importar `dados_tratados.csv` como tabela principal.
2. Importar `comparativo_mensal.csv` para criar paginas de evolucao temporal.
3. Usar `insights_gerenciais.csv` para montar uma pagina executiva com alertas e recomendacoes.
4. Consultar `graficos_sugeridos.csv` para escolher os visuais iniciais.
5. Usar `metadados.json` como referencia para entender quais colunas foram usadas como metrica, tempo e dimensao.

## Paginas sugeridas

- **Resumo executivo**: KPIs principais, qualidade geral, principais alertas e recomendacoes.
- **Comparativo mensal**: mes contra mes, acumulado do ano, media movel e variacao percentual.
- **Ranking gerencial**: produto, cliente, fornecedor, categoria ou outra dimensao relevante.
- **Qualidade dos dados**: nulos, duplicatas, outliers e pontos que exigem revisao.

## Medidas sugeridas

As medidas abaixo sao exemplos para copiar e adaptar no Power BI:

```DAX
Total Metrica = SUM(dados_tratados[Valor])

Media Metrica = AVERAGE(dados_tratados[Valor])

Variacao MoM = [Total Metrica] - CALCULATE([Total Metrica], DATEADD('Calendario'[Data], -1, MONTH))

Variacao MoM % = DIVIDE([Variacao MoM], CALCULATE([Total Metrica], DATEADD('Calendario'[Data], -1, MONTH)))

Acumulado Ano = TOTALYTD([Total Metrica], 'Calendario'[Data])
```

Os nomes das colunas devem ser ajustados de acordo com a base carregada.

## Status

Implementado na entrega `Adiciona comparativos mensais e pacote Power BI`.

