# Slide 1 - Multi-Modal Audio + Text Interview Analyzer
- Turns raw stakeholder interviews into structured qualitative insight in one CLI call.
- Automates transcription, summarization, theme discovery, quote surfacing, follow-ups, QA, and corrections.
- Built for desktop researchers who need fast synthesis without leaving their local environment.

---

# Slide 2 - Research Pain Points
- Hours of manual transcription, anonymization, and cleanup per interview.
- Insights get trapped in long-form notes with little thematic structure.
- Hard to compare new conversations against historical cohorts without a knowledge base.
- QA is ad hoc, so stakeholders distrust AI-written summaries.

---

# Slide 3 - Solution Overview
- `InterviewAnalysisPipeline.run` orchestrates chained agents (transcribe -> summarize -> themes -> quotes -> questions -> QA -> corrections).
- Works with either audio (wav/mp3/m4a/etc.) or existing transcripts (`.txt/.md/.json/.docx/.pdf`), including batch directory ingestion.
- Optional retrieval-augmented generation pulls similar past transcripts into every reasoning step.
- Outputs Markdown + JSON reports, clean & verbatim transcripts, and a QA log per run.

---

# Slide 4 - Pipeline Walkthrough
1. **Transcription Agent** (`gpt-4o-mini-transcribe`) creates labeled raw text and hands it to the formatter.
2. **Transcript Formatter** produces clean and verbatim variants (filler-aware, anonymized speakers).
3. **Summary + Theme Agents** craft short/long overviews and 3-6 evidence-backed themes.
4. **Quote Highlighter + Follow-Up Agents** extract emotional/behavioral quotes and suggest clarifying, probing, contrast questions.
5. **Quality Review + Correction Agents** audit the JSON/Markdown, flag issues, and auto-apply edits before saving artifacts.

---

# Slide 5 - Retrieval Augmented Insights
- Lightweight `InMemoryVectorStore` builds embeddings (`text-embedding-3-large`) for prior transcripts.
- CLI flags: `--enable-rag`, `--rag-dir`, `--rag-top-k`, `--rag-store-file`.
- Context block lists closest interviews with similarity scores and previews; injected into summary/theme prompts for contrastive insights.
- Store can persist to disk so subsequent runs avoid re-embedding unchanged transcripts.

---

# Slide 6 - CLI & Automation
```bash
python main.py \
  --audio data/sample.wav \
  --metadata participant=Alex cohort=Hikers \
  --enable-rag \
  --rag-dir data/previous_transcripts \
  --out-md reports/alex.md \
  --out-json reports/alex.json
```
- Replace `--audio` with repeated `--transcript` flags or `--transcript-dir-only` for text-only cohorts.
- `--aggregate-transcripts` + `--aggregate-name` creates cross-interview reports; `--aggregate-only` skips individual runs.
- Environment setup: `pip install -r requirements.txt`, add OpenAI key, install FFmpeg for pydub auto-chunking.

---

# Slide 7 - Collection Analyzer
- `TranscriptCollectionAnalyzer` batches transcripts into participant profiles with summaries and similarity links.
- Generates cohort-wide summary, notable pattern list, multi-participant themes, and spotlight quotes.
- Saves Markdown/JSON deliverables that complement per-interview reports (ideal for leadership readouts).

---

# Slide 8 - Deliverables & Storage
- Markdown reports (clean/original) under `reports/general/{clean,original}/`.
- Transcript exports (clean + verbatim) under `reports/transcripts/{clean,verbatim}/`.
- QA + reasoning logs in `reports/quality/`; JSON payloads when `--out-json` is provided.
- `data/rag_store.json` caches embeddings; audio + transcripts remain local for privacy.

---

# Slide 9 - Quality & Governance
- QA agent scores every run (status, severity, issue list) before anything ships.
- Correction agent rewrites markdown when QA requests fixes and appends a change log for traceability.
- Metadata propagation keeps source info (participant, cohort, file path) in the final report.
- Supports docx/pdf ingestion via `python-docx` and `pypdf`, preserving canonical transcripts.

---

# Slide 10 - Roadmap Ideas
1. Swap `InMemoryVectorStore` for a persistent vector DB when transcript volume spikes.
2. Add speaker diarization timestamps to power clip retrieval in downstream tooling.
3. Extend agents with tool-calling (e.g., CRM lookup, ticket filing) for seamless follow-up actions.
4. Ship a Streamlit/Gradio UI on top of the CLI for non-technical researchers.
