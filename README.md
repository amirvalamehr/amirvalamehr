### WheatNet: Boolean regulatory networks for wheat sucrose/starch metabolism

WheatNet is a small, runnable toolkit to simulate and optimize Boolean regulatory/logic circuits around sucrose and starch metabolism in wheat. It provides a safe Boolean evaluator, a synchronous update engine, a CLI, and example models.

### Quickstart

- Clone or open this repo.
- Run via module path without installation:

```bash
PYTHONPATH=src python3 -m wheatnet.cli simulate \
  --model examples/sucrose_starch.json \
  --steps 8 \
  --input-schedule examples/inputs_schedule.json \
  --print
```

- Export CSV:

```bash
PYTHONPATH=src python3 -m wheatnet.cli simulate \
  --model examples/sucrose_starch.json \
  --steps 16 \
  --input-schedule examples/inputs_schedule.json \
  --csv out.csv
```

### Optimize inputs

Random search over inputs to maximize a target node (default `Starch`).

```bash
PYTHONPATH=src python3 -m wheatnet.cli optimize \
  --model examples/sucrose_starch.json \
  --steps 16 \
  --mode constant \
  --iterations 512 \
  --objective final \
  --seed 1
```

Options:
- --mode: `constant` or `schedule` (per-step inputs)
- --objective: `final`, `sum`, or `mean`
- --target: node name to optimize

### Model format (JSON)

- `nodes`: list of node names
- `inputs`: list of input names
- `rules`: map of node -> Boolean expression using names, `and`, `or`, `not`

Example: see `examples/sucrose_starch.json`.

### Roadmap
- Parameter scan utilities and reproducible design spaces
- Hybrid discrete/real-valued gates and piecewise regulators
- Constraint-based optimization (ILP) for logic designs
- Visualization (network graph, time series)
- Domain model enrichment (enzyme/gene annotations)
