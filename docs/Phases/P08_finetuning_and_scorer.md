# P8. Fine-tuning and the scoring-model service: **Member 2** (M10t, M10)

> **Owner:** Member 2  
> Part of the CS4032 *Idea Generator with Go / No-Go* project. Rules: `../rule.md` · Checklist: `../project_completion.md` · Index: `../README.md`


**Goal:** a **cheaper, faster, more consistent** 1B–3B scorer that follows our rubric and evidence rule; **not** "smarter than hosted". **[G §6]**
**Depends on:** P3 (rubrics), P6 (cards + retrieval), P7 (hosted scorer as the baseline/teacher). **Done when:** the model runs in its own container behind `POST /score`, falls back to the hosted model on invalid output, and the **comparison table** (base vs fine-tuned vs hosted) is produced.

### Windows setup (training is **not** on the laptop)
- **Training:** free GPU on **Google Colab** (Runtime → Change runtime type → T4 GPU) or **Kaggle Notebooks** (GPU accelerator, weekly quota).
- **Laptop:** only prepares data, uploads it, downloads the result, and serves the quantised model on **CPU**.
```powershell
cd C:\dev\idea-validator\jobs\finetune
py -3.12 -m venv .venv ; .\.venv\Scripts\Activate.ps1
pip install pandas scikit-learn jsonschema httpx pytest
```
- Accounts needed: Google (Colab) or Kaggle; Hugging Face account/token for gated models (e.g. Llama) *(token goes in Colab secrets, never in git)*.

### 8A. Dataset (M10t) in `jobs/finetune/`
1. **Collect ≥ 300 (idea, evidence, dimension) examples** from the KB, covering **all 6 dimensions and all score levels 0–5** [B]. Aim for ~450 raw so ≥ 300 survive filtering. Include hard cases (thin evidence → low confidence/abstain, contradictory evidence).
2. **Draft labels with a hosted model** using the same rubric files (`rubrics/*.yaml`), JSON output only.
3. **Hand-check ≥ 60** and correct them; mark `"checked": true, "checked_by": "m1|m2"`. Split the checking between both members; these form the **evaluation set** [G].
4. **Split by idea, not row** (80/20, fixed seed): `train.jsonl`, `test.jsonl`, plus `manifest.json` listing idea ids per split. **Never use ideas from the labelled verdict set (P12)** → `scripts/check_leakage.py` fails if ids overlap.
5. **Format (one JSON object per line) [G §6.1]:**
   ```json
   {"messages":[
     {"role":"system","content":"Score the idea on demand_pain using rubric demand_pain@v3. Reply with JSON only."},
     {"role":"user","content":"IDEA: ... EVIDENCE: [card_8f21#c2] ... [card_77a1#c0] ..."},
     {"role":"assistant","content":"{\"score\":3.5,\"confidence\":0.7,\"evidence_ids\":[\"card_8f21#c2\"],\"reason\":\"...\"}"}]}
   ```
6. Validate every line with `jsonschema`; check the distribution table (dimension × score level) and put it in the report.

### 8B. Training (Colab/Kaggle)
1. Upload `train.jsonl`/`test.jsonl` (Colab Files panel or Google Drive).
2. Notebook `jobs/finetune/train.ipynb` + equivalent `train.py` (**both committed**): load a 1B–3B base (e.g. Llama-3.2-1B/3B-Instruct, Qwen2.5-1.5B/3B-Instruct, Gemma-2-2B) in **4-bit (QLoRA)** with **Unsloth** or **Hugging Face PEFT + TRL**.
3. Starting settings (record whatever you really use in `jobs/finetune/settings.json`): LoRA rank 16, alpha 32, dropout 0.05, learning rate 2e-4, **2–3 epochs**, effective batch 8 (grad accumulation), max sequence 2048. Watch **validation loss**; stop early if it rises.
4. **Merge** the adapter into the base model; **quantise to GGUF** (e.g. `q4_k_m`) so it runs on CPU.
5. Download `model.gguf` + `settings.json` + training curve. **Do not commit weights** [G]: upload `model.gguf` as a **GitHub Release asset** (or a registry) and put its link + SHA-256 in `jobs/finetune/MODEL.md`.

### 8C. Serving (M10, own container)
1. **Pod layout:** container `scorer` (FastAPI wrapper: `POST /score`, `/health`, `/ready`, `/metrics`) + sidecar `llama-server` (llama.cpp server image) loading the GGUF from a **PVC** (`/models`).
2. **Model import (no internet in the cluster):** copy the GGUF into the PVC with a helper pod:
   ```powershell
   kubectl apply -f k8s/model-import-pod.yaml                              # busybox pod mounting the models PVC
   kubectl cp .\model.gguf idea-validator/model-import:/models/model.gguf
   kubectl delete pod model-import -n idea-validator
   ```
3. `/score` flow **[G]:** build prompt from rubric + idea + evidence → call llama-server → **validate JSON against the schema** → if invalid, **retry once** → still invalid → **fall back to the hosted model (via M5)** and **log the fallback** (`fallbacks_total` metric + trace).
4. **Requests and limits from measurements:** run 50 scoring calls while `kubectl top pod -n idea-validator` samples every 10 s; set requests ≈ typical, limits ≈ 1.5× peak. Write the numbers into the report.

### 8D. Evaluation (**one table [G §6.3]**)
`jobs/evaluation/compare_models.py` runs **base**, **fine-tuned**, **hosted** on the hand-checked test set and writes `eval/results/model_comparison.json` + a Markdown table with: **MAE vs human**, **share within 1 point**, **valid-JSON rate**, **share of real evidence ids**, **latency**, **cost per score**.
- Add **one example where fine-tuning did not help** and explain why (mandatory in the report [B]).
- **Decision record #2:** *Fine-tuned scorer + hosted fallback* (numbers from the table).

**Screenshots:** the comparison table, `kubectl top` snapshot, a fallback event in the trace.
