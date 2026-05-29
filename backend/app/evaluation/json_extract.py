"""
Extração robusta de JSON da saída de um modelo.

Modelos reais (sobretudo com prompts CoT) raramente devolvem JSON puro: embrulham
em cercas markdown (```json ... ```) e/ou precedem com raciocínio em prosa. O
FakeAdapter devolve JSON limpo, então isso só aparece com provedores reais — é o
gap real-vs-fake. Os checks determinísticos precisam parsear o objeto JSON de fato
produzido, não falhar por causa do invólucro.

Estratégia conservadora (não inventa JSON; se não houver, devolve o texto original
e o `json.loads` do chamador falha corretamente):
  1. Se houver bloco cercado ```...```, usa o ÚLTIMO (em CoT o JSON vem por último).
  2. Senão, recorta do primeiro `{` ao último `}` (ou `[`..`]` para arrays).
  3. Senão, devolve o texto cru.
"""

from __future__ import annotations

import re

_FENCE_RE = re.compile(r"```(?:json|JSON)?\s*(.*?)```", re.DOTALL)


def extract_json_text(raw: str | None) -> str:
    """Devolve a melhor aproximação do trecho JSON dentro de `raw`."""
    if not raw:
        return ""
    text = raw.strip()

    # 1) bloco cercado — pega o último não-vazio
    fences: list[str] = [str(f).strip() for f in _FENCE_RE.findall(text)]
    fences = [f for f in fences if f]
    if fences:
        return fences[-1]

    # 2) objeto único: do primeiro { ao último }
    obj_start, obj_end = text.find("{"), text.rfind("}")
    if obj_start != -1 and obj_end > obj_start:
        return text[obj_start : obj_end + 1].strip()

    # 3) array: do primeiro [ ao último ]
    arr_start, arr_end = text.find("["), text.rfind("]")
    if arr_start != -1 and arr_end > arr_start:
        return text[arr_start : arr_end + 1].strip()

    # 4) nada reconhecível — devolve cru (o json.loads do chamador falhará)
    return text
