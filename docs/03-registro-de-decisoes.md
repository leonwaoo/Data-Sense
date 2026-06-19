# Registro de Decisoes

Este arquivo registra decisoes importantes do projeto para manter a evolucao documentada.

## Decisao 001: Projeto principal

Data: 2026-06-18.

Decisao: o projeto principal sera o DataSense.

Motivo: e o projeto com maior impacto para portfolio porque combina analise de dados, IA, visualizacao, qualidade de dados, Python, SQL e UX em uma experiencia unica.

## Decisao 002: Auditor de Dados como modulo interno

Data: 2026-06-18.

Decisao: o Auditor de Qualidade de Dados sera incluido como modulo do DataSense, nao como projeto separado no primeiro momento.

Motivo: a auditoria aumenta o valor pratico do produto e demonstra maturidade analitica, mas manter tudo em um produto evita dispersao de escopo.

## Decisao 003: MVP primeiro

Data: 2026-06-18.

Decisao: o desenvolvimento comecara pelo MVP com upload de CSV, perfil automatico, chat analitico, graficos basicos e auditoria de qualidade.

Motivo: o MVP permite validar rapidamente a ideia e criar uma versao demonstravel antes de adicionar funcionalidades avancadas.

## Decisao 004: Stack do backend

Data: 2026-06-18.

Decisao: o backend do MVP sera construido com Python, FastAPI, Pandas, DuckDB e Pydantic.

Motivo: essa combinacao permite criar uma API rapida, manipular dados com maturidade, executar consultas SQL sobre arquivos CSV e manter contratos de resposta claros para o frontend.

## Decisao 005: Stack do frontend

Data: 2026-06-18.

Decisao: o frontend do MVP sera construido com React, TypeScript, Vite, Recharts e CSS modular ou CSS organizado por componentes.

Motivo: essa stack e leve para desenvolvimento local, boa para portfolio, facilita componentes interativos e permite criar visualizacoes com uma experiencia fluida.

## Decisao 006: IA como camada assistida

Data: 2026-06-18.

Decisao: o chat analitico sera implementado em camadas. Primeiro, o sistema respondera perguntas suportadas por regras e consultas controladas. Depois, uma API de IA podera interpretar perguntas mais flexiveis e gerar explicacoes, sempre limitada a operacoes seguras.

Motivo: essa abordagem reduz risco de alucinacao, facilita testes e cria uma base demonstravel mesmo antes da integracao completa com IA.

## Decisao 007: Estrutura separada para backend e frontend

Data: 2026-06-18.

Decisao: o projeto sera organizado em `backend/`, `frontend/`, `data/` e `docs/`.

Motivo: essa divisao facilita evoluir API, interface, dados demonstrativos e documentacao sem misturar responsabilidades.

## Decisao 008: Dataset demonstrativo versionado

Data: 2026-06-18.

Decisao: o projeto tera um CSV ficticio de vendas em `data/sample/vendas_demo.csv`.

Motivo: o dataset permite demonstrar upload, perfil, auditoria de qualidade, perguntas analiticas e visualizacoes sem depender de arquivos externos.

## Decisao 009: Identidade visual do produto

Data: 2026-06-18.

Decisao: o nome publico do produto sera DataSense, com logo propria em SVG no frontend.

Motivo: o nome comunica analise de dados com mais personalidade para portfolio, sem depender de um termo generico de assistente.
