# Validation Dashboard

Concept validation dashboard that compares real customer feedback against AI-generated digital twin responses. Built with React (frontend) and Python (data pipeline).

## Structure

```
validation-dashboard/
├── dove-dashboard/          # React frontend (Vite + TypeScript)
├── scripts/                 # Python data pipeline (CSV → JSON)
├── testing/                 # Place real customer transcript CSVs here
├── step5_simulation_csvs/   # Place twin response CSVs here (1 per participant)
└── step5_per_twin_csvs/     # Place extended twin CSVs here (5 per participant)
```

## Setup

### 1. Python Data Pipeline

Processes CSV data files and generates JSON for the dashboard.

```bash
pip install -r scripts/requirements.txt
```

To run the pipeline (requires data files in `testing/`, `step5_simulation_csvs/`, `step5_per_twin_csvs/`):

```bash
ANTHROPIC_API_KEY=your-key python scripts/pipeline.py
```

This generates JSON files in `dove-dashboard/src/data/`.

### 2. React Dashboard

```bash
cd dove-dashboard
npm install
npm run dev
```

Opens at `http://localhost:5173/`

## Data Requirements

The dashboard expects these data files before running the pipeline:

- **`testing/`** — Real customer interview transcripts (CSV, one per participant)
- **`step5_simulation_csvs/`** — Twin responses (CSV, pattern: `P{XX}_T001_m8_qa_responses.csv`)
- **`step5_per_twin_csvs/`** — Extended twin responses (CSV, pattern: `P{XX}_T{YYY}_m8_qa_responses.csv`)

CSV columns expected: `module_id`, `question_text`, `answer_text`
