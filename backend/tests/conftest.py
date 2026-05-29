from __future__ import annotations

import os

# Forçar provider fake em todos os testes — nunca chamar API real.
os.environ.setdefault("MODEL_PROVIDER", "fake")
