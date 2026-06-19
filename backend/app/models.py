from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class DatasetSession:
    dataset_id: str
    file_name: str
    dataframe: pd.DataFrame

    def preview(self, rows: int = 10) -> list[dict]:
        safe_rows = max(1, min(rows, 50))
        preview_df = self.dataframe.head(safe_rows).where(pd.notnull(self.dataframe), None)
        return preview_df.to_dict(orient="records")

