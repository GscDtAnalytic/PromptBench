from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import get_db
from app.models import EvalResult, EvalRun

router = APIRouter(tags=["export"])


@router.get("/export/{run_id}")
async def export_run(
    run_id: int,
    format: str = Query(default="csv", pattern="^(csv|pdf)$"),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    run = await db.get(EvalRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run não encontrado")
    stmt = (
        select(EvalResult)
        .options(selectinload(EvalResult.test_case))
        .where(EvalResult.eval_run_id == run_id)
        .order_by(EvalResult.test_case_id, EvalResult.repetition_index)
    )
    rows = list((await db.execute(stmt)).scalars().all())

    if format == "csv":
        return _csv_response(rows, run_id)
    return _pdf_response(rows, run_id)


def _csv_response(rows: list[EvalResult], run_id: int) -> StreamingResponse:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "test_case_id",
            "slice",
            "repetition_index",
            "passed",
            "latency_ms",
            "input_tokens",
            "output_tokens",
            "cost_usd",
            "raw_output",
            "deterministic_scores",
            "rubric_scores",
            "error",
        ]
    )
    for r in rows:
        writer.writerow(
            [
                r.test_case_id,
                r.test_case.slice.value if r.test_case else "",
                r.repetition_index,
                r.passed,
                r.latency_ms,
                r.input_tokens,
                r.output_tokens,
                r.cost_usd,
                (r.raw_output or "")[:500],
                str(r.deterministic_scores or {})[:500],
                str(r.rubric_scores or {})[:500],
                r.error or "",
            ]
        )
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="run_{run_id}.csv"'},
    )


def _pdf_response(rows: list[EvalResult], run_id: int) -> StreamingResponse:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setFont("Helvetica", 14)
    c.drawString(40, 800, f"PromptBench — Run {run_id}")
    c.setFont("Helvetica", 9)
    y = 770
    for r in rows[:80]:
        line = (
            f"tc={r.test_case_id} rep={r.repetition_index} passed={r.passed} "
            f"lat={r.latency_ms}ms cost=${r.cost_usd or 0:.6f} "
            f"out={(r.raw_output or '')[:80]}"
        )
        c.drawString(40, y, line)
        y -= 12
        if y < 40:
            c.showPage()
            c.setFont("Helvetica", 9)
            y = 800
    c.save()
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="run_{run_id}.pdf"'},
    )
