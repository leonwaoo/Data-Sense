# Guia de contribuicao

## Convencao de mensagens de commit

Este projeto adota o padrao [Conventional Commits](https://www.conventionalcommits.org/),
escrito em portugues, no formato:

```
<tipo>(<escopo opcional>): <descricao no imperativo>

<corpo opcional explicando o que e por que>
```

### Tipos usados

- `feat`: nova funcionalidade
- `fix`: correcao de bug
- `docs`: apenas documentacao
- `style`: formatacao/estilo sem mudar logica
- `refactor`: refatoracao sem mudar comportamento
- `perf`: melhoria de desempenho
- `test`: adicao ou ajuste de testes
- `build`: build, dependencias ou empacotamento
- `chore`: tarefas de manutencao (configs, scripts, .gitignore)

### Escopos comuns

`frontend`, `backend`, `dashboard`, `report`, `analytics`, `docs`, `infra`.

### Exemplos

```
feat(dashboard): adiciona filtros de periodo e categoria
fix(backend): corrige soma indevida de colunas de NF
refactor(frontend): quebra App.tsx em componentes por dominio
docs(readme): documenta setup local do frontend
chore: ignora scripts locais de push
```

## Fluxo de trabalho

1. Crie uma branch a partir da `main`: `feat/<assunto>`, `fix/<assunto>`, etc.
2. Faca commits pequenos e descritivos seguindo a convencao acima.
3. Abra um Pull Request para a `main`.
4. Releases estaveis recebem uma tag anotada (`vX.Y`).
