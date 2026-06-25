from io import BytesIO

import pandas as pd
import pytest

from app.services import dataset_service
from app.services.dataset_service import get_dataset, load_dataset


def _csv_bytes(seed: int) -> bytes:
    return f"a,b\n{seed},{seed + 1}\n".encode()


def test_lru_eviction_respects_cap(monkeypatch) -> None:
    monkeypatch.setattr(dataset_service, "MAX_ACTIVE_DATASETS", 3)
    dataset_service._DATASETS.clear()

    ids = [load_dataset(_csv_bytes(i), f"f{i}.csv").dataset_id for i in range(5)]

    assert len(dataset_service._DATASETS) == 3
    assert ids[0] not in dataset_service._DATASETS
    assert ids[1] not in dataset_service._DATASETS
    assert ids[4] in dataset_service._DATASETS


def test_access_refreshes_recency(monkeypatch) -> None:
    monkeypatch.setattr(dataset_service, "MAX_ACTIVE_DATASETS", 2)
    dataset_service._DATASETS.clear()

    first = load_dataset(_csv_bytes(1), "a.csv").dataset_id
    second = load_dataset(_csv_bytes(2), "b.csv").dataset_id

    get_dataset(first)
    third = load_dataset(_csv_bytes(3), "c.csv").dataset_id

    assert first in dataset_service._DATASETS
    assert third in dataset_service._DATASETS
    assert second not in dataset_service._DATASETS


def test_load_dataset_rejects_empty_file() -> None:
    with pytest.raises(ValueError, match="vazio"):
        load_dataset(b"", "vazio.csv")


def test_load_dataset_rejects_unsupported_extension() -> None:
    with pytest.raises(ValueError, match="Formato nao suportado"):
        load_dataset(b"coluna\nvalor\n", "dados.pdf")


def test_load_dataset_rejects_malformed_json() -> None:
    with pytest.raises(ValueError, match="Nao foi possivel ler JSON"):
        load_dataset(b'{"produto": "Cafe", "valor": ', "dados.json")


def test_load_dataset_rejects_numeric_csv_without_header() -> None:
    with pytest.raises(ValueError, match="cabecalho confiavel"):
        load_dataset(b"1,2,3\n4,5,6\n", "sem_header.csv")


def test_load_dataset_accepts_single_column_csv_with_text_header() -> None:
    dataset = load_dataset("valor\n10\n20\n".encode("utf-8"), "uma_coluna.csv")

    assert dataset.dataframe.columns.tolist() == ["valor"]
    assert dataset.dataframe["valor"].tolist() == [10, 20]
    assert dataset.ingest_report["header_text_cells"] == 1
    assert dataset.ingest_report["header_numeric_cells"] == 0


def test_load_dataset_rejects_single_column_csv_without_text_header() -> None:
    with pytest.raises(ValueError, match="cabecalho confiavel"):
        load_dataset(b"10\n20\n30\n", "uma_coluna_sem_header.csv")


def test_load_dataset_detects_excel_header_after_decorative_title() -> None:
    buffer = BytesIO()
    dataframe = pd.DataFrame(
        [
            ["Relatorio gerencial de estoque", None, None],
            ["Produto", "Estoque Total (TON)", "Custo (R$/TON)"],
            ["Cafe", 1200, 450],
            ["Soja", 980, 510],
        ]
    )
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        dataframe.to_excel(writer, index=False, header=False)

    dataset = load_dataset(buffer.getvalue(), "dashboard.xlsx")

    assert dataset.dataframe.columns.tolist() == ["Produto", "Estoque Total (TON)", "Custo (R$/TON)"]
    assert dataset.dataframe.shape == (2, 3)
    assert dataset.ingest_report["metadata_rows_skipped"] == 1
    assert dataset.ingest_report["header_row_number"] == 2
