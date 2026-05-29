from __future__ import annotations

from pydantic import BaseModel


class RubricRead(BaseModel):
    """
    Metadata da rubrica usada para avaliar uma Task — exposta na UI para que o
    recrutador veja COMO o judge avalia (não só os resultados).
    """

    task_description: str
    rubric_criteria: str
    dimensions: list[str]
    weights: dict[str, float]
    anchors: str
