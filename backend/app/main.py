import os

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.services.analytics_service import answer_question
from app.services.chart_service import suggest_charts
from app.services.dataset_service import get_dataset, load_csv_dataset
from app.services.profile_service import build_profile
from app.services.quality_service import build_quality_report

app = FastAPI(
    title="DataSense API",
    description="API para upload, perfil, qualidade e perguntas analiticas sobre CSVs.",
    version="0.1.0",
)

DEFAULT_CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "").split(",")
    if origin.strip()
]
cors_origin_regex = os.getenv("CORS_ORIGIN_REGEX", r"https://.*\.vercel\.app")

app.add_middleware(
    CORSMiddleware,
    allow_origins=DEFAULT_CORS_ORIGINS + cors_origins,
    allow_origin_regex=cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict[str, str]:
    return {"name": "DataSense API", "health": "/health", "docs": "/docs"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/datasets/upload")
async def upload_dataset(file: UploadFile = File(...)) -> dict:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Envie um arquivo CSV valido.")

    content = await file.read()
    try:
        dataset = load_csv_dataset(content=content, file_name=file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "dataset_id": dataset.dataset_id,
        "file_name": dataset.file_name,
        "profile": build_profile(dataset),
        "preview": dataset.preview(),
        "quality": build_quality_report(dataset),
    }


@app.get("/datasets/{dataset_id}/profile")
def dataset_profile(dataset_id: str) -> dict:
    return build_profile(get_dataset(dataset_id))


@app.get("/datasets/{dataset_id}/preview")
def dataset_preview(dataset_id: str, rows: int = 10) -> list[dict]:
    return get_dataset(dataset_id).preview(rows=rows)


@app.get("/datasets/{dataset_id}/quality")
def dataset_quality(dataset_id: str) -> dict:
    return build_quality_report(get_dataset(dataset_id))


@app.post("/datasets/{dataset_id}/ask")
def ask_dataset(dataset_id: str, payload: dict) -> dict:
    question = str(payload.get("question", "")).strip()
    if not question:
        raise HTTPException(status_code=400, detail="Informe uma pergunta.")

    return answer_question(dataset=get_dataset(dataset_id), question=question)


@app.post("/datasets/{dataset_id}/charts/suggest")
def dataset_chart_suggestions(dataset_id: str) -> list[dict]:
    return suggest_charts(get_dataset(dataset_id))
