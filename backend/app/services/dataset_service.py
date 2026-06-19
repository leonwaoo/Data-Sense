import re
import unicodedata
import warnings
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pandas as pd
from fastapi import HTTPException

from app.models import DatasetSession

MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024
SUPPORTED_EXTENSIONS = {".csv", ".tsv", ".txt", ".xlsx", ".xls", ".json"}
_DATASETS: dict[str, DatasetSession] = {}


def load_dataset(content: bytes, file_name: str) -> DatasetSession:
    if not content:
        raise ValueError("O arquivo esta vazio.")
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise ValueError("O arquivo excede o limite inicial de 15 MB.")

    extension = Path(file_name).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError("Formato nao suportado. Envie CSV, TSV, TXT, XLSX, XLS ou JSON.")

    dataframe = _prepare_dataframe(_read_dataset(content=content, extension=extension))
    if dataframe.empty or not list(dataframe.columns):
        raise ValueError("O arquivo precisa conter colunas e pelo menos uma linha.")

    dataset = DatasetSession(
        dataset_id=str(uuid4()),
        file_name=file_name,
        dataframe=dataframe,
    )
    _DATASETS[dataset.dataset_id] = dataset
    return dataset


def supported_formats() -> list[str]:
    return sorted(SUPPORTED_EXTENSIONS)


def get_dataset(dataset_id: str) -> DatasetSession:
    dataset = _DATASETS.get(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset nao encontrado.")
    return dataset


def _read_dataset(content: bytes, extension: str) -> pd.DataFrame:
    if extension in {".csv", ".tsv", ".txt"}:
        return _read_delimited(content, extension)
    if extension in {".xlsx", ".xls"}:
        return _read_excel(content)
    if extension == ".json":
        return _read_json(content)

    raise ValueError("Formato nao suportado.")


def _read_delimited(content: bytes, extension: str) -> pd.DataFrame:
    encodings = ("utf-8", "utf-8-sig", "latin1")
    separators = ("\t",) if extension == ".tsv" else (None, ",", ";", "\t", "|")

    last_error: Exception | None = None
    for encoding in encodings:
        for separator in separators:
            try:
                dataframe = pd.read_csv(
                    BytesIO(content),
                    encoding=encoding,
                    sep=separator,
                    engine="python" if separator is None else "c",
                )
                if dataframe.shape[1] > 1 or separator == separators[-1]:
                    return dataframe
            except Exception as exc:  # pandas raises parser-specific exceptions.
                last_error = exc

    raise ValueError("Nao foi possivel ler o arquivo tabular. Verifique encoding e separador.") from last_error


def _read_excel(content: bytes) -> pd.DataFrame:
    try:
        sheets = pd.read_excel(BytesIO(content), sheet_name=None, header=None)
    except ImportError as exc:
        raise ValueError("Nao foi possivel ler Excel. Instale as dependencias openpyxl/xlrd do projeto.") from exc
    except Exception as exc:
        raise ValueError("Nao foi possivel ler o Excel. Verifique se a planilha esta valida.") from exc

    for dataframe in sheets.values():
        cleaned = _promote_detected_header(dataframe)
        if not cleaned.empty and list(cleaned.columns):
            return cleaned

    raise ValueError("A planilha Excel nao possui dados tabulares.")


def _read_json(content: bytes) -> pd.DataFrame:
    last_error: Exception | None = None
    for lines in (False, True):
        try:
            dataframe = pd.read_json(BytesIO(content), lines=lines)
            if isinstance(dataframe, pd.Series):
                dataframe = dataframe.to_frame()
            return dataframe
        except Exception as exc:
            last_error = exc

    raise ValueError("Nao foi possivel ler JSON. Use uma lista de objetos ou JSON Lines.") from last_error


def _prepare_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    dataframe = dataframe.copy()
    dataframe = dataframe.dropna(how="all").dropna(axis=1, how="all")
    dataframe.columns = _clean_columns(dataframe.columns)

    for column in dataframe.columns:
        if not _is_text_like(dataframe[column]) or _looks_like_identifier(column):
            continue

        cleaned = dataframe[column].map(_clean_text_cell)
        if _looks_like_date_column(column) or _looks_like_date_series(cleaned):
            dataframe[column] = cleaned
            continue

        numeric = _maybe_convert_numeric(cleaned)
        dataframe[column] = numeric if numeric is not None else cleaned

    return dataframe


def _promote_detected_header(dataframe: pd.DataFrame) -> pd.DataFrame:
    dataframe = dataframe.dropna(how="all").dropna(axis=1, how="all")
    if dataframe.empty:
        return dataframe

    header_index = _detect_header_row(dataframe)
    headers = dataframe.iloc[header_index].tolist()
    body = dataframe.iloc[header_index + 1 :].copy()
    body.columns = headers
    return body.dropna(how="all").dropna(axis=1, how="all")


def _detect_header_row(dataframe: pd.DataFrame) -> int:
    sample_size = min(len(dataframe), 12)
    scored_rows = [(_score_header_row(dataframe, row_index), row_index) for row_index in range(sample_size)]
    scored_rows.sort(reverse=True)
    return scored_rows[0][1] if scored_rows else 0


def _score_header_row(dataframe: pd.DataFrame, row_index: int) -> float:
    row = dataframe.iloc[row_index]
    values = [str(value).strip() for value in row.tolist() if pd.notna(value) and str(value).strip()]
    if not values:
        return -100

    non_empty_count = len(values)
    unique_count = len({_normalize_text(value) for value in values})
    numeric_count = sum(_looks_like_number(value) for value in values)
    known_terms = (
        "data",
        "mes",
        "trim",
        "trimestre",
        "nf",
        "nota",
        "produto",
        "cliente",
        "fornecedor",
        "valor",
        "receita",
        "venda",
        "compra",
        "prazo",
        "avaliacao",
        "status",
    )
    known_hits = sum(any(term in _normalize_text(value) for term in known_terms) for value in values)
    next_row_density = 0
    if row_index + 1 < len(dataframe):
        next_row_density = int(dataframe.iloc[row_index + 1].notna().sum())

    score = non_empty_count * 3 + unique_count + known_hits * 4 + min(next_row_density, non_empty_count) * 1.5
    score -= numeric_count * 2

    if non_empty_count <= 2 and any(len(value) > 28 for value in values):
        score -= 18
    if non_empty_count < 2:
        score -= 12

    return score


def _clean_columns(columns) -> list[str]:
    cleaned_columns: list[str] = []
    seen: dict[str, int] = {}

    for index, column in enumerate(columns, start=1):
        name = str(column).strip()
        if not name or name.lower().startswith("unnamed:"):
            name = f"coluna_{index}"

        count = seen.get(name, 0)
        seen[name] = count + 1
        cleaned_columns.append(name if count == 0 else f"{name}_{count + 1}")

    return cleaned_columns


def _is_text_like(series: pd.Series) -> bool:
    return pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)


def _looks_like_identifier(column: str) -> bool:
    normalized = _normalize_text(column)
    identifier_terms = ("id", "codigo", "cod", "sku", "cpf", "cnpj", "cep", "telefone", "phone")
    return any(term == normalized or normalized.startswith(f"{term}_") or normalized.endswith(f"_{term}") for term in identifier_terms)


def _looks_like_number(value: str) -> bool:
    return pd.notna(pd.to_numeric(_normalize_number(value), errors="coerce"))


def _looks_like_date_column(column: str) -> bool:
    normalized = _normalize_text(column)
    date_terms = ("data", "date", "mes", "month", "dia", "periodo", "competencia")
    return any(term == normalized or normalized.startswith(f"{term}_") or normalized.endswith(f"_{term}") for term in date_terms)


def _clean_text_cell(value):
    if not isinstance(value, str):
        return value

    value = value.strip()
    return pd.NA if value == "" else value


def _looks_like_date_series(series: pd.Series) -> bool:
    sample = series.dropna().astype(str).head(50)
    if sample.empty:
        return False

    date_patterns = (
        r"^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$",
        r"^\d{4}[/-]\d{1,2}[/-]\d{1,2}$",
        r"^\d{1,2}[/-]\d{4}$",
        r"^\d{4}[/-]\d{1,2}$",
    )
    if any(sample.str.match(pattern).mean() >= 0.8 for pattern in date_patterns):
        return True

    if sample.str.contains(r"[/-]").mean() < 0.8:
        return False

    parsed_dates = _parse_datetime(sample)
    if parsed_dates.notna().mean() < 0.5:
        parsed_dates = _parse_datetime(sample, dayfirst=True)

    return parsed_dates.notna().mean() >= 0.8


def _parse_datetime(series: pd.Series, dayfirst: bool = False) -> pd.Series:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        return pd.to_datetime(series, errors="coerce", dayfirst=dayfirst)


def _maybe_convert_numeric(series: pd.Series) -> pd.Series | None:
    non_null = series.dropna()
    if non_null.empty:
        return None

    normalized = series.map(_normalize_number)
    converted = pd.to_numeric(normalized, errors="coerce")
    success_ratio = converted.notna().sum() / len(non_null)
    if success_ratio >= 0.8:
        return converted

    return None


def _normalize_number(value):
    if value is None or value is pd.NA:
        return value
    if not isinstance(value, str):
        return value

    text = value.strip()
    if not text:
        return pd.NA

    negative = text.startswith("(") and text.endswith(")")
    text = re.sub(r"[^\d,.\-]", "", text)
    if negative:
        text = f"-{text}"
    if text in {"", "-", ".", ","}:
        return pd.NA

    has_comma = "," in text
    has_dot = "." in text

    if has_comma and has_dot:
        if text.rfind(",") > text.rfind("."):
            return text.replace(".", "").replace(",", ".")
        return text.replace(",", "")

    if has_comma:
        if re.fullmatch(r"-?\d{1,3}(,\d{3})+", text):
            return text.replace(",", "")
        return text.replace(",", ".")

    if has_dot and re.fullmatch(r"-?\d{1,3}(\.\d{3})+", text):
        return text.replace(".", "")

    return text


def _normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(character for character in text if not unicodedata.combining(character))
    text = re.sub(r"[^a-zA-Z0-9_]+", "_", text.lower())
    return re.sub(r"_+", "_", text).strip("_")
