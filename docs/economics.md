# Intervention economics

Original single-batch calculator (`/v1/economics/break-even`): expected avoided loss = baseline collapse probability
x effectiveness x loss; net value = avoided loss - cost; break-even baseline probability = cost / (effectiveness x loss).
The richer `/api/v1/economics/*` endpoints (break-even, sensitivity, uncertainty with EVPI) are described in
[Economic decision support](economic_decision_support.md). Both are scenario arithmetic with hypothetical inputs; they omit
treatment harms, false-positive costs, timing and operational constraints.
