# 📄 Final Advisory

* **Token usage advisory:** You’re fully green; tokens already emitted. When resuming in a fresh GPT, **seed with the block above** so Strategos picks up at *post-ADR-0001, STP4→STP5 transition*.
* **Startup configuration (recommended):** Start Strategos with the rehydration seed; route all execution to Pythagoras (Copilot). Enable PR-time CI to run `ops/audit/check_structure.sh` and `scripts/verify_workspace.sh` and require the four tokens in logs.
* **Assumptions & risks to validate on resume:**

  * CI gate for tokens not yet merged (optional but recommended).
  * HA add-on restart policy consistent after deploy (you restarted once; confirm this is automated if desired).
  * `.gitignore` guards remain to prevent re-introducing `addon/{ops,reports,.github,.vscode}`.

This package gives a parallel GPT everything needed to rehydrate context instantly and continue from the **STP4-strict graduation** objectives with governance intact.
