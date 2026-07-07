"""Reproduction of arXiv:2602.02868v1 — Quantum Information Flow in Microtubule
Tryptophan Networks (Gassab, Pusuluk & Craddock, 2026).

Subpackages:
  geometry  — Trp site positions/dipoles from PDB 1JFF and Appendix-A assembly
  couplings — Delta (Eq. 9) and G (Eq. 10) matrices, H_eff, decay decomposition
  model     — QuTiP Lindblad model, initial states, dynamics
  measures  — L1 coherence, correlated coherence, log-negativity, mutual info,
              trace-distance non-Markovian backflow (Appendix C)
"""

__all__ = ["geometry", "couplings", "model", "measures"]
