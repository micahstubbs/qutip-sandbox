# Security Audit Report: qutip-tutorials

**Audit Date:** 2026-07-07
**Project:** QuTiP tutorials — jupytext markdown notebooks for the Quantum Toolbox in Python
**Repository:** https://github.com/micahstubbs/qutip-tutorials (fork of https://github.com/qutip/qutip-tutorials)
**Auditor:** Claude Code Security Analysis

## Executive Summary

**VERDICT: CLEAN**

This is the official QuTiP organization's tutorials repository (audited as a same-day fork). It contains 176 jupytext markdown notebooks (tutorials-v4/ and tutorials-v5/), two small CI helper Python scripts, and a Jekyll website scaffold. All dependencies are pinned versions from official registries (PyPI, conda-forge, rubygems). No malware patterns, exfiltration vectors, obfuscated code, or suspicious install scripts were found.

## Project Overview

| Attribute | Value |
|-----------|-------|
| Language | Python (jupytext markdown notebooks) |
| Framework | QuTiP 4/5, Jupyter, Jekyll (website) |
| Purpose | Official tutorial notebooks for QuTiP |

## Dependency Analysis

- `requirements.txt`: qutip, qutip-qip, numpy, scipy, matplotlib, notebook, jupytext, black, flake8, nbqa, isort — all exact-pinned, all on PyPI. **SAFE**
- `environment.yml`: conda-forge channel only, same packages. **SAFE**
- `website/Gemfile`: `github-pages` from rubygems.org. **SAFE**
- No git/URL dependencies, no extra index URLs, no install hooks.

## Code Analysis

| Category | Status |
|----------|--------|
| Command Execution | None malicious — `eval()` appears only in tutorials evaluating user-typed quantum-state expressions (pedagogical, e.g. `qubism-and-schmidt-plots.md:377`) |
| Network Calls | Benign — `tools/report_failing_tests.py:21` posts a GitHub issue to `api.github.com/repos/qutip/qutip-jax` from scheduled CI; workflow `wget`s CSS/images from qutip.github.io |
| File Operations | Standard notebook plot/animation output only |
| Obfuscated Code | None — base64 usage embeds matplotlib animation video inline in lecture notebooks |
| Env Var Access | None detected |
| Hidden Files | Only `.jupytext` config and `.gitignore` |
| CI/CD | `.github/workflows/{notebook_ci,nightly_ci}.yaml` — standard test/build pipelines, no secrets exfiltration |

## Security Concerns

None.

## Recommendations

- Safe to create a virtualenv and execute notebooks. Note `requirements.txt` pins old versions (qutip 4.7.0, numpy 1.21) targeting the v4 notebooks; the tutorials-v5 set runs against qutip 5.
- The tutorial `eval()` cells only evaluate strings defined in the same notebook — no external input; no action needed.

## Conclusion

CLEAN. Proceed with dependency installation and notebook execution.
