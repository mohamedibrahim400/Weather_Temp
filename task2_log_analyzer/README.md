# Task 2 — Log File Analyzer (CLI)

## What it does
- Parses Apache/Nginx-style access logs.
- Outputs:
  - Total requests
  - Unique IPs
  - Most common endpoints
  - Status code breakdown
- Flags potential issues:
  - High 4xx/5xx error rate
  - Suspicious IP activity (high volume, high error rate, sensitive endpoints)
- Prints a readable console summary and writes a JSON report.

## Run (Python 3.13 + venv)
From the repository root:

```bash
cd nagwa
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python .\task2_log_analyzer\log_analyzer.py .\access.log --out report.json
```

## Quick demo (no input file needed)
```bash
python .\task2_log_analyzer\log_analyzer.py --demo --out report.json
```

## Common Windows path tips
- If your file path contains spaces, wrap it in quotes: `python .\task2_log_analyzer\log_analyzer.py "C:\Logs\access log.txt"`
- The example `path\to\access.log` is a placeholder; replace it with a real path.

## Read from stdin (no file needed)
```bash
python .\task2_log_analyzer\log_analyzer.py - --out report.json
```
Then paste log lines and press `Ctrl+Z` then `Enter` (Windows) to end input.

## Options
- `--top 15` to include more endpoints
- `--error-threshold 0.2` to change high-error flagging
