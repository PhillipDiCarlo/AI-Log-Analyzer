# AI Log Analyzer

A local, offline tool for analyzing application logs, detecting anomalies, and linking errors back to your codebase—powered by both keyword matching and semantic search. Works as both a CLI and a rich Tkinter GUI, with GPU‐accelerated embeddings (optional) and a dark‐mode UI.

---

## Features

- **Phase 1: Top Errors**  
  Count and rank the most common error/warning/exception messages in your logs.
- **Phase 2: Anomaly Detection**  
  Aggregate error counts per minute and flag statistical spikes.
- **Phase 3a: Keyword Linking**  
  Find log messages’ keywords in your code (skips `venv`, `.git`, `__pycache__`, `node_modules`, etc.).
- **Phase 3b: Semantic Linking**  
  Use FAISS + Sentence-Transformers to retrieve the most conceptually similar code snippets.
- **CLI & GUI**  
  - **CLI**: `python -m src.analyze_logs`  
  - **GUI**: interactive Tkinter app with dark‐mode, progress bar, CPU/GPU selector, chart embedding, and live log output.
- **GPU‐Accelerated Embeddings**  
  Optional CUDA support for super‐fast indexing & queries on your NVIDIA card.
- **Modular & Test-Driven**  
  Fully tested with pytest and organized into reusable modules.

---

## Requirements

All dependencies are managed in `requirements.txt`. To install:

```bash
pip uninstall -y torch torchvision torchaudio
pip install -r requirements.txt
