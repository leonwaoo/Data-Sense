# DataSense Copilot

Projeto de portfolio em Data Science e Gestao da Informacao.

O DataSense Copilot e uma aplicacao onde o usuario faz upload de um arquivo CSV e conversa com os dados em linguagem natural. A ferramenta gera respostas analiticas, graficos, insights, auditoria de qualidade dos dados e recomendacoes praticas.

## Objetivo

Criar um produto demonstravel para entrevistas e processos seletivos, mostrando habilidades em:

- Python para tratamento e analise de dados.
- SQL para consultas estruturadas.
- Visualizacao de dados.
- Inteligencia artificial aplicada a analise exploratoria.
- Auditoria e qualidade de dados.
- UX voltada para usuarios de negocio.
- Documentacao tecnica e de produto.

## Problema

Muitas pessoas e empresas possuem dados em planilhas, mas nao sabem transformar esses dados rapidamente em perguntas respondidas, graficos, diagnosticos e decisoes. O projeto resolve esse problema oferecendo uma experiencia simples: enviar um CSV, perguntar em linguagem natural e receber uma analise confiavel.

## Solucao

O sistema atuara como um copilot para analise de dados:

- Le o CSV enviado pelo usuario.
- Identifica colunas, tipos de dados, valores ausentes e possiveis problemas.
- Permite perguntas em linguagem natural sobre os dados.
- Gera consultas, tabelas resumidas, graficos e explicacoes.
- Detecta anomalias e problemas de qualidade.
- Sugere proximas analises e recomendacoes de negocio.

## Documentacao

- [Definicao do projeto](docs/01-definicao-do-projeto.md)
- [Roadmap](docs/02-roadmap.md)
- [Registro de decisoes](docs/03-registro-de-decisoes.md)
- [Definicao tecnica do MVP](docs/04-definicao-tecnica-mvp.md)

## Estrutura inicial

```text
backend/
  app/
    main.py
    services/
frontend/
  src/
data/
  sample/
    vendas_demo.csv
docs/
```

## Como executar localmente

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

A API ficara disponivel em:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/docs`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Se preferir usar pnpm:

```bash
cd frontend
pnpm install
pnpm run dev
```

O frontend ficara disponivel em:

- `http://localhost:5173`

### Identidade visual

O projeto usa o nome DataSense Copilot e possui logo em SVG nos arquivos:

- `frontend/public/brand-mark.svg`
- `frontend/public/logo-datasense.svg`

### Dataset demonstrativo

Use o arquivo:

- `data/sample/vendas_demo.csv`

Ele possui vendas ficticias com produto, categoria, regiao, faturamento, valores ausentes, duplicata e outlier simples para demonstrar o MVP.

## Status

Fase atual: MVP funcional em desenvolvimento, com upload de CSV, perfil automatico, auditoria de qualidade, chat analitico e sugestoes de graficos.
