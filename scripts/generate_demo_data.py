from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = ROOT / "data" / "sample"
PUBLIC_SAMPLE_DIR = ROOT / "frontend" / "public" / "samples"


def main() -> None:
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    PUBLIC_SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

    vendas = pd.read_csv(SAMPLE_DIR / "vendas_demo.csv")
    vendas.to_excel(SAMPLE_DIR / "vendas_demo.xlsx", index=False)

    compras = pd.DataFrame(
        [
            ["2026-01-04", "Alpha Supply", "Insumos", "Operacoes", "Aprovado", 42, 1840.50, "Boleto"],
            ["2026-01-09", "Beta Tech", "Tecnologia", "TI", "Aprovado", 8, 5220.00, "Cartao"],
            ["2026-01-17", "Delta Office", "Escritorio", "Administrativo", "Aprovado", 30, 960.00, "Pix"],
            ["2026-02-02", "Alpha Supply", "Insumos", "Operacoes", "Aprovado", 38, 1710.00, "Boleto"],
            ["2026-02-12", "Gamma Logistics", "Frete", "Logistica", "Pendente", 6, 2450.00, "Boleto"],
            ["2026-02-20", "Beta Tech", "Tecnologia", "TI", "Aprovado", 4, 3180.00, "Cartao"],
            ["2026-03-03", "Delta Office", "Escritorio", "Administrativo", "Aprovado", 45, 1350.00, "Pix"],
            ["2026-03-11", "Gamma Logistics", "Frete", "Logistica", "Aprovado", 9, 3720.00, "Boleto"],
            ["2026-03-18", "Alpha Supply", "Insumos", "Operacoes", "Cancelado", 12, 0.00, "Boleto"],
            ["2026-04-07", "Beta Tech", "Tecnologia", "TI", "Aprovado", 10, 7400.00, "Cartao"],
            ["2026-04-16", "Omega Services", "Servicos", "Marketing", "Aprovado", 3, 4200.00, "Pix"],
            ["2026-04-27", "Gamma Logistics", "Frete", "Logistica", "Aprovado", 7, 2880.00, "Boleto"],
        ],
        columns=[
            "data_compra",
            "fornecedor",
            "categoria",
            "centro_custo",
            "status",
            "quantidade",
            "valor_compra",
            "forma_pagamento",
        ],
    )
    compras.to_csv(SAMPLE_DIR / "compras_demo.csv", index=False, sep=";", decimal=",")
    compras.to_excel(SAMPLE_DIR / "compras_demo.xlsx", index=False)

    clientes = pd.DataFrame(
        [
            ["2026-01-02", "Acme Corp", "Enterprise", "Sao Paulo", "SP", "Ativo", 42800.00, 7, "Baixo"],
            ["2026-01-08", "Norte Solar", "SMB", "Belem", "PA", "Ativo", 12600.00, 3, "Medio"],
            ["2026-01-21", "Clinica Boa Vista", "Saude", "Recife", "PE", "Ativo", 23800.00, 5, "Baixo"],
            ["2026-02-06", "Futura Edu", "Educacao", "Curitiba", "PR", "Inativo", 5200.00, 1, "Alto"],
            ["2026-02-19", "Mercado Central", "Varejo", "Rio de Janeiro", "RJ", "Ativo", 31600.00, 6, "Medio"],
            ["2026-03-04", "Log Prime", "Logistica", "Goiania", "GO", "Ativo", 18450.00, 4, "Baixo"],
            ["2026-03-16", "Construtora Leste", "Enterprise", "Salvador", "BA", "Ativo", 55200.00, 8, "Baixo"],
            ["2026-04-01", "Studio Pixel", "SMB", "Florianopolis", "SC", "Ativo", 9800.00, 2, "Medio"],
            ["2026-04-15", "Agro Vale", "Agro", "Uberlandia", "MG", "Ativo", 27300.00, 4, "Baixo"],
            ["2026-05-02", "Rede Mais", "Varejo", "Fortaleza", "CE", "Inativo", 7600.00, 2, "Alto"],
        ],
        columns=[
            "data_cadastro",
            "cliente",
            "segmento",
            "cidade",
            "estado",
            "status",
            "receita",
            "tickets",
            "risco_churn",
        ],
    )
    clientes_records = clientes.to_dict(orient="records")
    (SAMPLE_DIR / "clientes_demo.json").write_text(
        json.dumps(clientes_records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    estoque = pd.DataFrame(
        [
            ["2026-01", "Notebook Pro", "Eletronicos", 14, 8, 6, 16, 4200.00, 67200.00, "Saudavel"],
            ["2026-01", "Monitor 27", "Eletronicos", 22, 10, 9, 23, 880.00, 20240.00, "Saudavel"],
            ["2026-01", "Cadeira Ergo", "Moveis", 18, 7, 10, 15, 520.00, 7800.00, "Atencao"],
            ["2026-02", "Notebook Pro", "Eletronicos", 16, 12, 9, 19, 4200.00, 79800.00, "Saudavel"],
            ["2026-02", "Mouse Sem Fio", "Acessorios", 80, 35, 42, 73, 65.00, 4745.00, "Saudavel"],
            ["2026-02", "Headset Pro", "Acessorios", 26, 12, 18, 20, 145.00, 2900.00, "Atencao"],
            ["2026-03", "Servidor Mini", "Eletronicos", 4, 2, 5, 1, 14200.00, 14200.00, "Critico"],
            ["2026-03", "Mesa Ajustavel", "Moveis", 9, 6, 7, 8, 980.00, 7840.00, "Atencao"],
            ["2026-03", "Teclado Mecanico", "Acessorios", 38, 20, 18, 40, 210.00, 8400.00, "Saudavel"],
        ],
        columns=[
            "mes",
            "produto",
            "categoria",
            "estoque_inicial",
            "entradas",
            "saidas",
            "estoque_final",
            "custo_unitario",
            "valor_total",
            "status",
        ],
    )
    estoque.to_csv(SAMPLE_DIR / "estoque_financeiro_demo.tsv", index=False, sep="\t")

    for path in SAMPLE_DIR.iterdir():
        if path.is_file() and path.suffix.lower() in {".csv", ".tsv", ".xlsx", ".json"}:
            (PUBLIC_SAMPLE_DIR / path.name).write_bytes(path.read_bytes())


if __name__ == "__main__":
    main()
