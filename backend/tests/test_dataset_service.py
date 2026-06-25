from app.services import dataset_service
from app.services.dataset_service import get_dataset, load_dataset


def _csv_bytes(seed: int) -> bytes:
    return f"a,b\n{seed},{seed + 1}\n".encode()


def test_lru_eviction_respects_cap(monkeypatch) -> None:
    monkeypatch.setattr(dataset_service, "MAX_ACTIVE_DATASETS", 3)
    dataset_service._DATASETS.clear()

    ids = [load_dataset(_csv_bytes(i), f"f{i}.csv").dataset_id for i in range(5)]

    assert len(dataset_service._DATASETS) == 3
    # Os dois datasets mais antigos foram descartados.
    assert ids[0] not in dataset_service._DATASETS
    assert ids[1] not in dataset_service._DATASETS
    # O mais recente continua disponivel.
    assert ids[4] in dataset_service._DATASETS


def test_access_refreshes_recency(monkeypatch) -> None:
    monkeypatch.setattr(dataset_service, "MAX_ACTIVE_DATASETS", 2)
    dataset_service._DATASETS.clear()

    first = load_dataset(_csv_bytes(1), "a.csv").dataset_id
    second = load_dataset(_csv_bytes(2), "b.csv").dataset_id

    # Acessar 'first' o torna o mais recente; o proximo upload deve descartar 'second'.
    get_dataset(first)
    third = load_dataset(_csv_bytes(3), "c.csv").dataset_id

    assert first in dataset_service._DATASETS
    assert third in dataset_service._DATASETS
    assert second not in dataset_service._DATASETS
