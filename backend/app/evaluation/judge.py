"""
RubricJudge — LLM-as-a-judge com signature tipada (estilo DSPy).

Contrato:
    Inputs:  RubricInputs(task_description, test_case_input, candidate_output, rubric_criteria)
    Outputs: RubricOutputs(quality, instruction_adherence, factual_structural, tone_format, reasoning)
             ou RubricError(judge_error: str) se o judge não retornar JSON válido após 1 retry.

Regras invioláveis (CLAUDE.md §2.2):
- O judge NUNCA inventa nota. Se o JSON for inválido → marca `judge_error` e propaga.
- temperature baixa (default 0.0).
- Avalia dimensões de forma INDEPENDENTE (anti halo effect) — instrução explícita no prompt.
- Many-shot anchors (bom/médio/ruim) calibram a escala 1-5.
- CoT campo a campo antes da nota; cada nota cita evidência.

A interface aceita um `ModelAdapter` injetado. Em testes, passamos um FakeAdapter
roteirizado ou uma stub. Em prod, ClaudeAdapter/OpenAIAdapter.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from app.adapters.base import ModelAdapter


@dataclass
class RubricInputs:
    task_description: str
    test_case_input: dict[str, Any]
    candidate_output: str
    rubric_criteria: str


@dataclass
class RubricOutputs:
    quality: int  # 1-5
    instruction_adherence: int  # 1-5
    factual_structural: int  # 1-5
    tone_format: int  # 1-5
    reasoning: str

    @property
    def is_error(self) -> bool:
        return False


@dataclass
class RubricError:
    judge_error: str
    raw_response: str = ""

    @property
    def is_error(self) -> bool:
        return True


RubricResult = RubricOutputs | RubricError


# =====================================================================
# Many-shot anchors (calibração da escala 1-5)
# =====================================================================

ANCHORS = """
ÂNCORAS DE CALIBRAÇÃO (use para ancorar suas notas):

Anchor BOM (notas 5):
  Output: {"match_score": 78, "matched_skills": ["Python","SQL"], "missing_skills": ["AWS"],
          "ranking_justification": "Cobre Python (5 anos comprovados) e SQL; falta AWS que era requisito."}
  Notas: quality=5, instruction_adherence=5, factual_structural=5, tone_format=5
  Razão: JSON limpo, justificativa cita evidência, sem alucinação, formato exato.

Anchor MÉDIO (notas 3):
  Output: {"match_score": 80, "matched_skills": ["Python","SQL","Docker"], "missing_skills": [],
          "ranking_justification": "Candidato adequado."}
  Notas: quality=3, instruction_adherence=4, factual_structural=2, tone_format=4
  Razão: formato OK, mas Docker não aparece no currículo (alucinação leve)
         e a justificativa é vaga.

Anchor RUIM (notas 1-2):
  Output: "O candidato é bom. Score: 100."
  Notas: quality=2, instruction_adherence=1, factual_structural=1, tone_format=1
  Razão: não é JSON, score sem critério, sem campos obrigatórios.
"""


def _build_judge_prompt(inp: RubricInputs) -> tuple[str, str]:
    system = (
        "Você é um avaliador rigoroso de outputs de LLM. Sua tarefa é dar notas "
        "1-5 em quatro dimensões INDEPENDENTES, raciocinando campo a campo ANTES de "
        "emitir cada nota e citando evidência do output. NUNCA infle uma dimensão "
        "porque outra foi boa (anti halo effect). Se o output tiver problemas em "
        "alguma dimensão, isso NÃO afeta as outras. "
        "Retorne apenas JSON válido conforme o schema solicitado."
    )

    user = f"""
TAREFA:
{inp.task_description}

CRITÉRIOS DA RUBRICA:
{inp.rubric_criteria}

{ANCHORS}

INPUT DO TESTE:
{json.dumps(inp.test_case_input, ensure_ascii=False, indent=2)}

OUTPUT CANDIDATO:
{inp.candidate_output}

INSTRUÇÕES:
1. Para cada dimensão, escreva 1-2 frases de raciocínio citando evidência do output.
2. Em seguida emita uma nota inteira de 1 a 5.
3. Avalie as dimensões SEPARADAMENTE (não deixe que uma boa nota arraste as outras).

Responda APENAS com JSON neste formato exato:
{{
  "reasoning": "<seu raciocínio campo a campo>",
  "quality": <1-5>,
  "instruction_adherence": <1-5>,
  "factual_structural": <1-5>,
  "tone_format": <1-5>
}}
""".strip()

    return system, user


# =====================================================================
# Parser + validador
# =====================================================================

_JSON_RE = re.compile(r"\{[\s\S]*\}")


def _extract_json(text: str) -> dict[str, Any] | None:
    def _parse(s: str) -> dict[str, Any] | None:
        try:
            data = json.loads(s)
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, dict) else None

    parsed = _parse(text)
    if parsed is not None:
        return parsed
    m = _JSON_RE.search(text)
    return _parse(m.group(0)) if m else None


def _validate(payload: dict[str, Any]) -> RubricOutputs | None:
    required = {"quality", "instruction_adherence", "factual_structural", "tone_format"}
    if not required.issubset(payload):
        return None
    try:
        scores = {k: int(payload[k]) for k in required}
    except (TypeError, ValueError):
        return None
    for v in scores.values():
        if v < 1 or v > 5:
            return None
    reasoning = str(payload.get("reasoning", ""))
    return RubricOutputs(
        quality=scores["quality"],
        instruction_adherence=scores["instruction_adherence"],
        factual_structural=scores["factual_structural"],
        tone_format=scores["tone_format"],
        reasoning=reasoning,
    )


# =====================================================================
# Judge runner
# =====================================================================


@dataclass
class RubricJudge:
    adapter: ModelAdapter
    temperature: float = 0.0
    max_tokens: int = 600
    # quantas re-tentativas após parse fail (além da primeira)
    retries: int = 1

    async def judge(self, inputs: RubricInputs) -> RubricResult:
        system, user = _build_judge_prompt(inputs)
        last_raw = ""

        for attempt in range(self.retries + 1):
            extra_user = (
                user
                if attempt == 0
                else (
                    user
                    + "\n\nSua resposta anterior NÃO foi JSON válido. "
                    "Tente novamente e retorne SOMENTE o JSON, sem texto adicional."
                )
            )
            response = await self.adapter.call(
                system=system,
                user=extra_user,
                params={"temperature": self.temperature, "max_tokens": self.max_tokens},
            )
            last_raw = response.text
            payload = _extract_json(last_raw)
            if payload is None:
                continue
            validated = _validate(payload)
            if validated is not None:
                return validated

        return RubricError(
            judge_error="JSON inválido ou notas fora do range 1-5 após retries",
            raw_response=last_raw,
        )
