from io import BytesIO
from uuid import uuid4

import pandas as pd
from fastapi import HTTPException

from app.models import DatasetSession

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
_DATASETS: dict[str, DatasetSession] = {}


def load_csv_dataset(content: bytes, file_name: str) -> DatasetSession:
    if not content:
        raise ValueError("O arquivo esta vazio.")
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise ValueError("O arquivo excede o limite inicial de 10 MB.")

    dataframe = _read_csv(content)
    if dataframe.empty or not list(dataframe.columns):
        raise ValueError("O CSV precisa conter colunas e pelo menos uma linha.")

    dataset = DatasetSession(
        dataset_id=str(uuid4()),
        file_name=file_name,
        dataframe=dataframe,
    )
    _DATASETS[dataset.dataset_id] = dataset
    return dataset


def get_dataset(dataset_id: str) -> DatasetSession:
    dataset = _DATASETS.get(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset nao encontrado.")
    return dataset


def _read_csv(content: bytes) -> pd.DataFrame:
    encodings = ("utf-8", "utf-8-sig", "latin1")
    separators = (None, ",", ";", "\t")

    last_error: Exception | None = None
    for encoding in encodings:
        for separator in separators:
            try:
                return pd.read_csv(
                    BytesIO(content),
                    encoding=encoding,
                    sep=separator,
                    engine="python" if separator is None else "c",
                )
            except Exception as exc:  # pandas raises parser-specific exceptions.
                last_error = exc

    raise ValueError("Nao foi possivel ler o CSV. Verifique encoding e separador.") from last_error

