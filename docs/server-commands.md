# Server Commands Log

## 2026-07-07 — corsair-7000d: qutip-tutorials notebook run (qutip-sandbox-j0c.4)

Set up and ran the full tutorials-v5 notebook suite on corsair-7000d (Ubuntu 24.04, 32 cores, 62GB).

```bash
# Clone fork and create venv (Python 3.12.3)
ssh corsair-7000d
mkdir -p ~/wk/qutip-sandbox-corsair && cd ~/wk/qutip-sandbox-corsair
git clone https://github.com/micahstubbs/qutip-tutorials.git
python3.12 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install qutip matplotlib jupytext nbclient nbformat ipykernel \
  ipywidgets mpmath qutip-qip qutip-qoc qutip-qtrl jax diffrax qutip-jax
# → qutip 5.3.0

# Runner script copied from this repo (scripts/run_tutorial_notebooks.py) with
# ROOT/TUTORIALS paths adjusted for the flat layout (no scripts/ subdir):
scp scripts/run_tutorial_notebooks.py corsair-7000d:~/wk/qutip-sandbox-corsair/

# Full run: 97 notebooks, 6 workers, 600s timeout each
cd ~/wk/qutip-sandbox-corsair
MPLBACKEND=Agg nohup .venv/bin/python run_tutorial_notebooks.py \
  --set v5 --timeout 600 --workers 6 > output/notebook-runs/run-v5.log 2>&1 &
# pid 373177; results: output/notebook-runs/results-v5.jsonl,
# report: docs/notebook-run-results-v5.md
```
