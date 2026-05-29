"""
Valida datasets JSONL:
- cada linha é JSON válido
- chaves obrigatórias presentes (id, slice, input, rubric_notes)
- slice ∈ enum
- distribuição de slices dentro de ±5pp do alvo 60/20/10/10
- ids únicos

Uso:
  python -m scripts.validate_datasets
"""

from __future__ import annotations

import json
from pathlib import Path

# Scripts vivem em backend/scripts/; datasets vivem na raiz do repo.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATASETS_DIR = Path("/datasets") if Path("/datasets").exists() else REPO_ROOT / "datasets"

VALID_SLICES = {"typical", "edge", "known_failure", "adversarial"}
TARGET_DISTRIBUTION = {
    "typical": 0.60,
    "edge": 0.20,
    "known_failure": 0.10,
    "adversarial": 0.10,
}
TOLERANCE_PP = 0.05

REQUIRED_KEYS = {"id", "slice", "input", "rubric_notes"}


def validate(path: Path) -> tuple[bool, list[str], dict[str, int]]:
    errors: list[str] = []
    ids: set[str] = set()
    distribution: dict[str, int] = dict.fromkeys(VALID_SLICES, 0)

    with path.open("r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as e:
                errors.append(f"L{line_num}: JSON inválido: {e}")
                continue

            missing = REQUIRED_KEYS - set(row.keys())
            if missing:
                errors.append(f"L{line_num}: faltando keys {missing}")
                continue

            row_id = row["id"]
            if row_id in ids:
                errors.append(f"L{line_num}: id duplicado '{row_id}'")
            ids.add(row_id)

            slice_label = row["slice"]
            if slice_label not in VALID_SLICES:
                errors.append(
                    f"L{line_num}: slice inválido '{slice_label}' (esperado: {sorted(VALID_SLICES)})"
                )
                continue
            distribution[slice_label] += 1

    total = sum(distribution.values())
    if total == 0:
        errors.append("dataset vazio")
        return False, errors, distribution

    for slice_label, target_pct in TARGET_DISTRIBUTION.items():
        actual_pct = distribution[slice_label] / total
        if abs(actual_pct - target_pct) > TOLERANCE_PP:
            errors.append(
                f"distribuição de '{slice_label}': {actual_pct:.0%} fora de "
                f"{target_pct:.0%} ±{TOLERANCE_PP:.0%} (atual: {distribution[slice_label]}/{total})"
            )

    return len(errors) == 0, errors, distribution


def main() -> int:
    overall_ok = True
    for path in sorted(DATASETS_DIR.glob("*.jsonl")):
        ok, errors, distribution = validate(path)
        total = sum(distribution.values())
        print(f"\n=== {path.name} — {total} casos ===")
        for slice_label, count in sorted(distribution.items()):
            pct = count / total if total else 0
            print(f"  {slice_label:14}: {count:3}  ({pct:.0%})")
        if ok:
            print("  status: OK")
        else:
            print("  status: FALHOU")
            for e in errors:
                print(f"    - {e}")
            overall_ok = False
    print("\n" + ("=== TUDO OK ===" if overall_ok else "=== FALHAS PRESENTES ==="))
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
