import csv
import re
import warnings
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd
from fastapi import HTTPException

from app.models import DatasetSession
from app.services.column_heuristics import looks_like_identifier as _looks_like_identifier
from app.services.column_heuristics import normalize_text as _normalize_text

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

    raw_dataframe, ingest_report = _read_dataset(content=content, extension=extension)
    dataframe = _prepare_dataframe(raw_dataframe)
    if dataframe.empty or not list(dataframe.columns):
        raise ValueError("O arquivo precisa conter colunas e pelo menos uma linha.")

    ingest_report = _finalize_ingest_report(ingest_report, raw_dataframe, dataframe)
    dataset = DatasetSession(
        dataset_id=str(uuid4()),
        file_name=file_name,
        dataframe=dataframe,
        ingest_report=ingest_report,
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


def _read_dataset(content: bytes, extension: str) -> tuple[pd.DataFrame, dict]:
    if extension in {".csv", ".tsv", ".txt"}:
        return _read_delimited(content, extension)
    if extension in {".xlsx", ".xls"}:
        return _read_excel(content, extension)
    if extension == ".json":
        return _read_json(content)

    raise ValueError("Formato nao suportado.")


def _read_delimited(content: bytes, extension: str) -> tuple[pd.DataFrame, dict]:
    encodings = ("utf-8-sig", "utf-8", "latin1")
    separators = ("\t",) if extension == ".tsv" else (None, ",", ";", "\t", "|")

    last_error: Exception | None = None
    candidates: list[tuple[float, pd.DataFrame, dict]] = []
    for encoding in encodings:
        for separator in separators:
            try:
                dataframe, detected_separator = _read_delimited_table(content, encoding, separator)
                cleaned, header_report = _promote_detected_header(dataframe)
                report = {
                    "extension": extension,
                    "source_type": "delimited",
                    "encoding": encoding,
                    "separator": detected_separator,
                    "raw_rows_estimate": int(_replace_blank_cells(dataframe).dropna(how="all").shape[0]),
                    **header_report,
                }
                candidates.append((_table_candidate_score(cleaned, report), cleaned, report))
            except Exception as exc:  # pandas raises parser-specific exceptions.
                last_error = exc

    if candidates:
        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1], candidates[0][2]

    raise ValueError("Nao foi possivel ler o arquivo tabular. Verifique encoding e separador.") from last_error


def _read_delimited_table(content: bytes, encoding: str, separator: str | None) -> tuple[pd.DataFrame, str]:
    text = content.decode(encoding)
    detected_separator = separator or _sniff_separator(text)
    reader = csv.reader(StringIO(text), delimiter=detected_separator)
    rows = [row for row in reader]
    if not rows:
        return pd.DataFrame(), detected_separator

    max_columns = max(len(row) for row in rows)
    padded_rows = [row + [pd.NA] * (max_columns - len(row)) for row in rows]
    return pd.DataFrame(padded_rows, dtype=object), detected_separator


def _sniff_separator(text: str) -> str:
    sample = "\n".join(text.splitlines()[:25])
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        return dialect.delimiter
    except csv.Error:
        scores = {separator: sample.count(separator) for separator in [",", ";", "\t", "|"]}
        return max(scores.items(), key=lambda item: item[1])[0]


def _read_excel(content: bytes, extension: str) -> tuple[pd.DataFrame, dict]:
    try:
        sheets = pd.read_excel(BytesIO(content), sheet_name=None, header=None)
    except ImportError as exc:
        raise ValueError("Nao foi possivel ler Excel. Instale as dependencias openpyxl/xlrd do projeto.") from exc
    except Exception as exc:
        raise ValueError("Nao foi possivel ler o Excel. Verifique se a planilha esta valida.") from exc

    candidates: list[tuple[float, pd.DataFrame, dict]] = []
    for sheet_name, dataframe in sheets.items():
        cleaned, header_report = _promote_detected_header(dataframe)
        if not cleaned.empty and list(cleaned.columns):
            report = {
                "extension": extension,
                "source_type": "excel",
                "sheet_name": str(sheet_name),
                "raw_rows_estimate": int(_replace_blank_cells(dataframe).dropna(how="all").shape[0]),
                **header_report,
            }
            candidates.append((_table_candidate_score(cleaned, report), cleaned, report))

    if candidates:
        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1], candidates[0][2]

    raise ValueError("A planilha Excel nao possui dados tabulares.")


def _read_json(content: bytes) -> tuple[pd.DataFrame, dict]:
    last_error: Exception | None = None
    for lines in (False, True):
        try:
            dataframe = pd.read_json(BytesIO(content), lines=lines)
            if isinstance(dataframe, pd.Series):
                dataframe = dataframe.to_frame()
            return dataframe, {
                "extension": ".json",
                "source_type": "json_lines" if lines else "json",
                "raw_rows_estimate": int(dataframe.shape[0]),
                "header_row_index": None,
                "header_row_number": None,
                "metadata_rows_skipped": 0,
                "header_confidence": 1.0,
                "warnings": [],
            }
        except Exception as exc:
            last_error = exc

    raise ValueError("Nao foi possivel ler JSON. Use uma lista de objetos ou JSON Lines.") from last_error


def _prepare_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    dataframe = dataframe.copy()
    dataframe = _replace_blank_cells(dataframe).dropna(how="all").dropna(axis=1, how="all")
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

    return dataframe.reset_index(drop=True)


def _promote_detected_header(dataframe: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    dataframe = _replace_blank_cells(dataframe)
    dataframe = dataframe.dropna(how="all").dropna(axis=1, how="all")
    if dataframe.empty:
        return dataframe, {
            "header_row_index": None,
            "header_row_number": None,
            "metadata_rows_skipped": 0,
            "header_confidence": 0.0,
            "source_columns_estimate": 0,
            "warnings": ["Nao foram encontradas linhas tabulares nao vazias."],
        }

    header_index, header_score = _detect_header_row(dataframe)
    headers = dataframe.iloc[header_index].tolist()
    body = dataframe.iloc[header_index + 1 :].copy()
    body.columns = headers
    body = body.dropna(how="all").dropna(axis=1, how="all")

    warnings_list: list[str] = []
    if header_index > 0:
        warnings_list.append(
            f"Foram ignorada(s) {header_index} linha(s) antes do cabecalho detectado."
        )

    return body, {
        "header_row_index": int(header_index),
        "header_row_number": int(header_index + 1),
        "metadata_rows_skipped": int(header_index),
        "header_confidence": _header_confidence(header_score),
        "source_columns_estimate": int(dataframe.shape[1]),
        "warnings": warnings_list,
    }


def _detect_header_row(dataframe: pd.DataFrame) -> tuple[int, float]:
    sample_size = min(len(dataframe), 12)
    scored_rows = [(_score_header_row(dataframe, row_index), row_index) for row_index in range(sample_size)]
    scored_rows.sort(reverse=True)
    if not scored_rows:
        return 0, 0.0
    return scored_rows[0][1], scored_rows[0][0]


def _score_header_row(dataframe: pd.DataFrame, row_index: int) -> float:
    row = dataframe.iloc[row_index]
    values = [str(value).strip() for value in row.tolist() if pd.notna(value) and str(value).strip()]
    if not values:
        return -100

    non_empty_count = len(values)
    normalized_values = [_normalize_text(value) for value in values]
    unique_count = len({value for value in normalized_values if value})
    numeric_count = sum(_looks_like_number(value) for value in values)
    text_count = sum(bool(re.search(r"[A-Za-z_]", value)) for value in values)
    short_label_count = sum(1 for value in values if 1 <= len(value) <= 36)
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
    next_row_data_like = 0
    if row_index + 1 < len(dataframe):
        next_values = [
            str(value).strip()
            for value in dataframe.iloc[row_index + 1].tolist()
            if pd.notna(value) and str(value).strip()
        ]
        next_row_density = len(next_values)
        next_row_data_like = sum(_looks_like_number(value) or _looks_like_date_cell(value) for value in next_values)

    distinct_ratio = unique_count / max(non_empty_count, 1)
    text_ratio = text_count / max(non_empty_count, 1)
    short_ratio = short_label_count / max(non_empty_count, 1)
    score = (
        non_empty_count * 3
        + unique_count * 1.5
        + known_hits * 5
        + min(next_row_density, non_empty_count) * 2
        + next_row_data_like * 1.5
        + distinct_ratio * 8
        + text_ratio * 8
        + short_ratio * 6
    )
    score -= numeric_count * 4

    if non_empty_count <= 2 and any(len(value) > 28 for value in values):
        score -= 28
    if non_empty_count < 2:
        score -= 20
    if distinct_ratio < 0.75:
        score -= 14
    if text_ratio < 0.6:
        score -= 18
    if any(len(value) > 64 for value in values):
        score -= 12

    return score


def _replace_blank_cells(dataframe: pd.DataFrame) -> pd.DataFrame:
    return dataframe.apply(
        lambda column: column.map(
            lambda value: pd.NA if isinstance(value, str) and not value.strip() else value
        )
    )


def _looks_like_date_cell(value: str) -> bool:
    return bool(
        re.match(r"^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$", value)
        or re.match(r"^\d{4}[/-]\d{1,2}[/-]\d{1,2}$", value)
        or re.match(r"^\d{4}[/-]\d{1,2}$", value)
        or re.match(r"^\d{1,2}[/-]\d{4}$", value)
        or re.match(r"^(q|t|tri|trim)?[1-4][\s_/-]?\d{2,4}$", value, flags=re.IGNORECASE)
    )


def _header_confidence(score: float) -> float:
    return round(max(0.0, min(1.0, score / 95)), 2)


def _table_candidate_score(dataframe: pd.DataFrame, report: dict) -> float:
    if dataframe.empty:
        return -1000.0

    columns = _clean_columns(dataframe.columns)
    generic_columns = sum(1 for column in columns if _normalize_text(column).startswith("coluna_"))
    cells = max(dataframe.shape[0] * dataframe.shape[1], 1)
    density = float(dataframe.notna().sum().sum() / cells)
    score = dataframe.shape[1] * 10 + min(dataframe.shape[0], 500) * 0.05 + density * 40
    score += float(report.get("header_confidence") or 0) * 35
    score -= generic_columns * 8
    if dataframe.shape[1] <= 1:
        score -= 35
    return score


def _finalize_ingest_report(report: dict, raw_dataframe: pd.DataFrame, dataframe: pd.DataFrame) -> dict:
    warnings_list = list(report.get("warnings", []))
    raw_rows = report.get("raw_rows_estimate")
    metadata_rows = int(report.get("metadata_rows_skipped") or 0)
    header_row_index = report.get("header_row_index")
    parsed_rows = int(dataframe.shape[0])
    rows_after_header = int(raw_dataframe.shape[0])
    expected_data_rows = None
    if isinstance(raw_rows, int):
        expected_data_rows = max(raw_rows - metadata_rows - (1 if header_row_index is not None else 0), 0)
        if expected_data_rows != parsed_rows:
            warnings_list.append(
                "A contagem de linhas mudou apos a ingestao: "
                f"{raw_rows} linha(s) bruta(s), {expected_data_rows} linha(s) esperada(s) depois do cabecalho "
                f"e {parsed_rows} registro(s) analisado(s)."
            )

    generic_columns = [column for column in dataframe.columns if _normalize_text(column).startswith("coluna_")]
    if generic_columns:
        warnings_list.append(
            "Ainda existem nomes genericos de coluna; confira se o cabecalho real foi identificado corretamente."
        )

    return {
        **report,
        "parsed_rows": parsed_rows,
        "parsed_columns": int(dataframe.shape[1]),
        "rows_after_header": rows_after_header,
        "expected_data_rows": expected_data_rows,
        "blank_rows_dropped": max(rows_after_header - parsed_rows, 0),
        "empty_columns_dropped": max(int(report.get("source_columns_estimate") or raw_dataframe.shape[1]) - dataframe.shape[1], 0),
        "warnings": _deduplicate_messages(warnings_list),
    }


def _deduplicate_messages(messages: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for message in messages:
        key = _normalize_text(message)
        if not message or key in seen:
            continue
        seen.add(key)
        result.append(message)
    return result


def _clean_columns(columns) -> list[str]:
    cleaned_columns: list[str] = []
    seen: dict[str, int] = {}

    for index, column in enumerate(columns, start=1):
        if _is_missing_header(column):
            name = ""
        else:
            name = str(column).strip().lstrip("\ufeff")
        if not name or name.lower() in {"nan", "none", "<na>"} or name.lower().startswith("unnamed:"):
            name = f"coluna_{index}"

        count = seen.get(name, 0)
        seen[name] = count + 1
        cleaned_columns.append(name if count == 0 else f"{name}_{count + 1}")

    return cleaned_columns


def _is_missing_header(value: Any) -> bool:
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _is_text_like(series: pd.Series) -> bool:
    return pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)


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
