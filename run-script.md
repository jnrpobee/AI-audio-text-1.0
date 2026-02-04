# Run Script

```bash
python main.py \ # Run the main script
  --audio data/sample.wav \
  --metadata participant=Alex cohort=Hikers \
  --out-md reports/alex.md \
  --out-json reports/alex.json \
  --transcript-dir reports/transcripts \
  --quality-report-dir reports/quality \
  --enable-rag \
  --rag-dir data/previous_transcripts
```

main.py is the main script that runs the pipeline.
audio is the path to the interview audio file.
metadata is the optional metadata entries as key=value pairs.
out-md is the optional path to save a Markdown report.
out-json is the optional path to save the structured JSON.
transcript-dir is the directory where raw + formatted transcript text files are stored.
quality-report-dir is the directory where quality and reasoning reports are stored.
enable-rag is the flag to enable retrieval augmented context from past transcripts.
rag-dir is the directory containing previous transcripts (.txt/.md/.json) to ingest.

## Example

- To transcribe the interview audio file and save the report in the reports/"filename".**md** file, run the following example command:
---✅✅✅ ---

```bash
python main.py --audio data\P3-audio.m4a --out-md reports\P3-interview-4.md
```

- To transcribe the interview audio file and save the report in the reports/"filename".**json** file, run the following example command:
---✅✅✅ ---

```bash
python main.py --audio data\P3-audio.m4a --out-json reports\P3-interview-4.json
```

- To transcribe the interview audio file and save the report in the reports/"filename".**md** file and the structured JSON in the reports/"filename".**json** file, run the following example command:
---✅✅✅ ---

```bash
python main.py --audio data\P3-audio.m4a --out-md reports\P3-interview-4.md --out-json reports\P3-interview-4.json
```

--- 

## RAG Workflow

--- this section transcribes the audio file and saves the report in the reports/"filename".md file and the structured JSON in the reports/"filename".json file ---✅✅✅

- To enable retrieval augmented context from past transcripts, run the following example command:

```bash
python main.py --audio data\P3-audio.m4a --out-md reports\P3-interview-4.md --out-json reports\P3-interview-4.json --enable-rag --rag-dir data\previous_transcripts
```

- To store the embeddings of the previous transcripts in a JSON file, run the following example command:

```bash
python main.py --audio data\P3-audio.m4a --out-md reports\P3-interview-4.md --out-json reports\P3-interview-4.json --enable-rag --rag-dir data\previous_transcripts --rag-store-file data\rag_store.json
```

## running multiple transcripts without audio input

- To run multiple transcripts without audio input, run the following example command:
- run the following example command:

```bash
python main.py --transcript-dir-only data\previous_transcripts --enable-rag --rag-dir data\previous_transcripts
```

- To run multiple transcripts without audio input and save the report in the reports/"filename".md file, run the following example command:

```bash
python main.py --transcript-dir-only data\previous_transcripts --enable-rag --rag-dir data\previous_transcripts --out-md reports\P3-interview-4.md
```

--- running multiple transcripts with audio input ---✅✅✅

- To run multiple transcripts without audio input and save the report in the reports/"filename".json file, run the following example command:

```bash
python main.py --transcript-dir-only data\previous_transcripts --aggregate-transcripts --aggregate-only --aggregate-name test-themes-1 --enable-rag --rag-dir data\previous_transcripts --rag-store-file data\rag_store.json    
```
