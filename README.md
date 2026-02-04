## Multi-Modal Audio + Text Interview Analyzer

An end-to-end, multi-agent pipeline that turns raw interview audio into structured qualitative insights. The system:

- Generates clean transcripts from audio (multimodal completion).
- Produces both short and long summaries.
- Extracts 3–6 themed insights with representative quotes.
- Highlights emotionally salient or behavior-describing quotes.
- Suggests clarifying, probing, and contrast follow-up questions.
- Optionally loads previous transcripts into an embedding store to add RAG context for comparisons.

### 1. Setup

```bash
pip install -r requirements.txt
```

> **Heads-up:** Long-form transcription now auto-chunks via `pydub`. Install [FFmpeg](https://ffmpeg.org/download.html) and keep it on your PATH so `pydub` can decode `.wav/.m4a/.mp3` inputs.
> Transcript ingestion supports `.txt`, `.md`, `.json`, plus `.docx` (requires `python-docx`) and `.pdf` (requires `pypdf`) which are already included in `requirements.txt`.

Export your OpenAI key (or place it in `env/.env`).

```bash
# PowerShell
Copy-Item env/.env.example env/.env
notepad env/.env  # add OPENAI_API_KEY=sk-...

# or export directly
setx OPENAI_API_KEY "sk-..."
```

### 2. Running the pipeline

```bash
python main.py \
  --audio data/sample.wav \
  --metadata participant=Alex cohort=Hikers \
  --out-md reports/alex.md \
  --out-json reports/alex.json \
  --transcript-dir reports/transcripts \
  --quality-report-dir reports/quality \
  --enable-rag \
  --rag-dir data/previous_transcripts \
  --rag-store-file data/rag_store.json
```

CLI flags:

- `--audio`: interview audio file. Any format supported by GPT-4o transcribe (wav, mp3, m4a, etc.). Optional if you supply transcripts directly.
- `--transcript`: path to a transcript (`.txt/.md/.json/.docx/.pdf`) to analyze without audio. Repeat this flag to process multiple files.
- `--transcript-dir-only`: analyze every transcript file in the specified directory (recursively) without providing audio. Supports `.txt`, `.md`, `.json`, `.docx`, and `.pdf`.
- `--metadata key=value`: optional metadata recorded in the output.
- `--context-hint`: short text to guide the transcription model (e.g., study name).
- `--enable-rag`: turn on context retrieval from previous transcripts.
- `--rag-dir`: directory containing `.txt`, `.md`, or `.json` transcripts for ingestion.
- `--rag-top-k`: number of similar transcripts to surface when RAG is enabled.
- `--rag-store-file`: optional JSON cache where embeddings of previous transcripts are saved/reused between runs.
- `--out-md / --out-json`: save the markdown or JSON report. Defaults to printing markdown to stdout.
- `--transcript-dir`: parent folder that receives two subfolders per run:
  - `clean/`: anonymized, speaker-labeled transcripts (`*_clean.txt`) that remove filler words but preserve intent.
  - `verbatim/`: fully detailed, speaker-labeled transcripts (`*_verbatim.txt`) that preserve every utterance.
  Defaults to `reports/transcripts`.
- `--report-dir`: when you omit `--out-md`, reports are saved automatically beneath this directory (default `reports/`); transcript-only runs go into `<report_dir>/general/`.
- `--aggregate-transcripts`: when processing multiple transcripts, also generate a single combined report that highlights cross-interview summaries, themes, and quotes.
- `--aggregate-name`: filename stem for the combined report (defaults to `combined`).
- `--aggregate-only`: skip individual transcript reports and produce only the combined analysis (useful for large cohorts).
- `--quality-report-dir`: folder storing the QA + correction reasoning report (`*_quality.md`). Defaults to `reports/quality`.
- Clean/original reports: whenever you pass `--out-md`, the CLI now also writes two copies of the full analysis under `<report_dir>/clean/` (with the cleaned transcript) and `<report_dir>/original/` (with the verbatim, speaker-labeled transcript), so stakeholders can choose their preferred view.

**Transcripts-only example**

```bash
python main.py \
  --transcript-dir-only data/previous_transcripts \
  --aggregate-transcripts \
  --aggregate-name cohort-summary \
  --aggregate-only \
  --enable-rag \
  --rag-dir data/previous_transcripts \
  --rag-store-file data/rag_store.json
```

This processes every transcript file in `data/previous_transcripts/`, produces only the combined “cohort-summary” report (clean + verbatim copies), and uses the same folder for contextual comparisons. Remove `--aggregate-only` if you also want per-file reports.

### 3. Agents & Responsibilities

1. **Transcription Agent** (`gpt-4o-mini-transcribe`): Multimodal completion that converts the supplied audio into a speaker-aware transcript.
2. **Summary Agent**: Produces a concise (3‑4 sentence) and detailed (1 paragraph) summary.
3. **Theme Extraction Agent**: Surfaces 3–6 themes, attaches qualitative frequency, and quotes as evidence.
4. **Quote Highlighter Agent**: Tags memorable, emotional, and behavioral quotes with rationales/suggested uses.
5. **Follow-Up Question Agent**: Creates clarifying, probing, and contrast interview questions.
6. **Transcript Formatter Agent**: Converts the raw transcript into an anonymous, speaker-labeled script (`Interviewer:` / `Participant:`) so it’s easy to scan without exposing identities. The pipeline saves both the formatted and raw versions under the transcript directory.
7. **Quality Review Agent**: Audits the structured + markdown output, catching missing sections, unclear writing, or formatting problems and returns concrete recommendations.
8. **Correction Agent**: Applies the QA recommendations, fixes the markdown report, and logs the adjustments. When a correction is applied, the saved markdown defaults to the revised version.

Every stage runs automatically inside `InterviewAnalysisPipeline.run`, so a single CLI call runs the full multi-agent workflow.

All reasoning agents use JSON-mode responses via the Responses API, making downstream parsing dependable.

### 4. Optional RAG Workflow

If you have previous transcripts, drop them (txt/md/json) into a folder and pass `--enable-rag --rag-dir path`. The pipeline will:

1. Embed each transcript with `text-embedding-3-large`.
2. Retrieve the top-K similar interviews for the new transcript.
3. Feed that context into the summary and theme agents so they can call out recurring patterns or contrasts.

This is a lightweight numpy-backed store (`InMemoryVectorStore`) meant for desktop research workflows. Swap it with your preferred vector DB if needed.

**Tip:** Supply `--rag-store-file data/rag_store.json` so embeddings are cached between runs. The first invocation embeds everything inside `--rag-dir`; future runs reuse the cache unless new transcripts are added (in which case they are embedded and the cache is updated automatically).

### 5. Automated QA & Corrections

After the core agents finish, the QA agent inspects the JSON + markdown and reports issues/severity plus actionable recommendations. When the QA status is not `"pass"`, the correction agent rewrites the markdown, applies the fixes, and appends a change log. Even when everything passes, the QA summary is embedded at the bottom of the report for auditability.

### 6. Saving / Post-processing

`InterviewAnalysisResult` (returned by `pipeline.run`) offers:

- `to_markdown()` / `save_markdown(path)`
- `to_json()` / `save_json(path)`

Use these helpers to integrate with downstream dashboards or note-taking tools.

### 7. Extending the System

- Swap models in `audio_transcript/config.py`.
- Inject a custom vector store by passing `rag_store` into `InterviewAnalysisPipeline`.
- Add tool calls (e.g., timestamp lookup, file archiving) by extending the agents and wiring them into `pipeline.py`.

### 8. Caveats

- You need audio files locally; the CLI does not download them.
- Running RAG over many transcripts will incur embedding costs; use sparingly or cache embeddings if needed.
- The pipeline assumes English by default, but GPT-4o transcription handles multiple languages—pass `--context-hint "Language: Spanish"` for better accuracy.
- Audio files longer than ~23 minutes are automatically chunked into ~20-minute slices. This requires FFmpeg; without it you'll see a runtime error when the fallback kicks in.
