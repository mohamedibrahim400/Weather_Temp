from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


LOG_PATTERN = re.compile(
    r'^(?P<ip>\S+)\s+\S+\s+\S+\s+\[(?P<time>[^\]]+)\]\s+"(?P<method>\S+)\s+(?P<path>\S+)(?:\s+(?P<proto>[^"]+))?"\s+(?P<status>\d{3})\s+(?P<size>\S+)',
)

SUSPICIOUS_PATH_SNIPPETS = (
    "/admin",
    "/wp-admin",
    "/wp-login",
    "/phpmyadmin",
    "/.env",
    "/login",
)

DEMO_LINES = [
    '127.0.0.1 - - [10/Oct/2024:13:55:36 +0000] "GET / HTTP/1.1" 200 1024',
    '127.0.0.1 - - [10/Oct/2024:13:55:37 +0000] "GET /products?category=oil HTTP/1.1" 200 2048',
    '10.0.0.5 - - [10/Oct/2024:13:55:40 +0000] "GET /admin HTTP/1.1" 403 512',
    '10.0.0.5 - - [10/Oct/2024:13:55:41 +0000] "GET /wp-login.php HTTP/1.1" 404 321',
    '10.0.0.5 - - [10/Oct/2024:13:55:42 +0000] "GET /.env HTTP/1.1" 404 123',
    '203.0.113.9 - - [10/Oct/2024:13:56:00 +0000] "POST /login HTTP/1.1" 500 900',
    '203.0.113.9 - - [10/Oct/2024:13:56:10 +0000] "GET /api/orders HTTP/1.1" 200 777',
]


@dataclass(frozen=True)
class LogEntry:
    ip: str
    timestamp_raw: str
    method: str
    path: str
    status: int
    size: int | None


@dataclass(frozen=True)
class SuspiciousIp:
    ip: str
    requests: int
    error_rate: float
    suspicious_path_hits: int


def _strip_query(path: str) -> str:
    return path.split("?", 1)[0]


def _parse_size(value: str) -> int | None:
    if value == "-":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def parse_log_line(line: str) -> LogEntry | None:
    match = LOG_PATTERN.match(line.strip())
    if not match:
        return None

    path = match.group("path")
    status = int(match.group("status"))
    size = _parse_size(match.group("size"))

    return LogEntry(
        ip=match.group("ip"),
        timestamp_raw=match.group("time"),
        method=match.group("method"),
        path=path,
        status=status,
        size=size,
    )


def read_lines(input_path: str) -> Iterable[str]:
    if input_path == "-":
        yield from sys.stdin
        return

    path = Path(input_path)
    with path.open("r", encoding="utf-8", errors="replace") as f:
        yield from f


def _try_parse_apache_time(value: str) -> datetime | None:
    try:
        return datetime.strptime(value, "%d/%b/%Y:%H:%M:%S %z")
    except ValueError:
        return None


def analyze(lines: Iterable[str], *, top_n: int, error_rate_threshold: float) -> dict[str, Any]:
    total_lines = 0
    parsed = 0
    parse_failures = 0

    endpoints = Counter()
    status_codes = Counter()
    ips = Counter()
    ip_errors = Counter()
    ip_suspicious_hits = Counter()

    time_first: datetime | None = None
    time_last: datetime | None = None

    for line in lines:
        total_lines += 1
        entry = parse_log_line(line)
        if entry is None:
            parse_failures += 1
            continue
        parsed += 1

        endpoint = _strip_query(entry.path)
        endpoints[endpoint] += 1
        status_codes[str(entry.status)] += 1
        ips[entry.ip] += 1

        if 400 <= entry.status <= 599:
            ip_errors[entry.ip] += 1

        if any(snippet in endpoint for snippet in SUSPICIOUS_PATH_SNIPPETS):
            ip_suspicious_hits[entry.ip] += 1

        ts = _try_parse_apache_time(entry.timestamp_raw)
        if ts is not None:
            if time_first is None or ts < time_first:
                time_first = ts
            if time_last is None or ts > time_last:
                time_last = ts

    total_requests = parsed
    unique_ips = len(ips)
    error_requests = sum(int(v) for k, v in status_codes.items() if k.startswith(("4", "5")))
    error_rate = (error_requests / total_requests) if total_requests else 0.0

    issues: list[dict[str, Any]] = []
    if total_requests == 0:
        issues.append({"type": "no_data", "message": "No valid log lines were parsed."})
    elif error_rate >= error_rate_threshold:
        issues.append(
            {
                "type": "high_error_rate",
                "message": "High proportion of 4xx/5xx responses.",
                "error_rate": round(error_rate, 4),
                "threshold": error_rate_threshold,
            }
        )

    suspicious_ips: list[SuspiciousIp] = []
    if total_requests:
        suspicious_volume_threshold = max(100, int(0.2 * total_requests))
        for ip, req_count in ips.most_common():
            err_count = ip_errors.get(ip, 0)
            ip_err_rate = (err_count / req_count) if req_count else 0.0
            suspicious_hits = ip_suspicious_hits.get(ip, 0)

            is_suspicious = (
                req_count >= suspicious_volume_threshold
                or (req_count >= 20 and ip_err_rate >= 0.3)
                or suspicious_hits >= 5
            )
            if is_suspicious:
                suspicious_ips.append(
                    SuspiciousIp(
                        ip=ip,
                        requests=req_count,
                        error_rate=round(ip_err_rate, 4),
                        suspicious_path_hits=int(suspicious_hits),
                    )
                )

        if suspicious_ips:
            issues.append(
                {
                    "type": "suspicious_ip_activity",
                    "message": "IPs with unusual volume/errors/sensitive endpoints.",
                    "ips": [asdict(x) for x in suspicious_ips[:20]],
                    "volume_threshold": suspicious_volume_threshold,
                }
            )

    report: dict[str, Any] = {
        "summary": {
            "total_lines": total_lines,
            "parsed_requests": total_requests,
            "parse_failures": parse_failures,
            "unique_ips": unique_ips,
            "error_rate_4xx_5xx": round(error_rate, 4),
            "time_range": {
                "first": time_first.isoformat() if time_first else None,
                "last": time_last.isoformat() if time_last else None,
            },
        },
        "top_endpoints": [{"endpoint": ep, "count": c} for ep, c in endpoints.most_common(top_n)],
        "status_code_breakdown": dict(status_codes),
        "top_ips": [{"ip": ip, "count": c} for ip, c in ips.most_common(10)],
        "issues": issues,
    }
    return report


def print_console_report(report: dict[str, Any]) -> None:
    summary = report["summary"]
    print("Log Analysis Report")
    print("=" * 20)
    print(f"Total lines:           {summary['total_lines']}")
    print(f"Parsed requests:       {summary['parsed_requests']}")
    print(f"Parse failures:        {summary['parse_failures']}")
    print(f"Unique IPs:            {summary['unique_ips']}")
    print(f"Error rate (4xx/5xx):  {summary['error_rate_4xx_5xx']}")

    tr = summary.get("time_range") or {}
    if tr.get("first") and tr.get("last"):
        print(f"Time range:            {tr['first']} -> {tr['last']}")

    print()
    print("Top endpoints")
    print("-" * 20)
    for item in report.get("top_endpoints", []):
        print(f"{item['count']:>6}  {item['endpoint']}")

    print()
    print("Status codes")
    print("-" * 20)
    for code, count in sorted(report.get("status_code_breakdown", {}).items()):
        print(f"{code:>3}: {count}")

    issues = report.get("issues", [])
    if issues:
        print()
        print("Potential issues")
        print("-" * 20)
        for issue in issues:
            msg = issue.get("message") or issue.get("type", "issue")
            print(f"- {msg}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze Apache/Nginx access logs and output a JSON report.")
    parser.add_argument(
        "logfile",
        nargs="?",
        default="-",
        help="Path to access log file, or '-' to read from stdin. Ignored when --demo is used.",
    )
    parser.add_argument("--out", default="report.json", help="Output JSON file path. Default: report.json")
    parser.add_argument("--top", type=int, default=10, help="Top N endpoints to include. Default: 10")
    parser.add_argument(
        "--error-threshold",
        type=float,
        default=0.10,
        help="Flag high error rate if (4xx+5xx)/requests >= threshold. Default: 0.10",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run on built-in demo log lines (no input file needed).",
    )
    args = parser.parse_args()

    try:
        if args.demo:
            report = analyze(DEMO_LINES, top_n=args.top, error_rate_threshold=args.error_threshold)
        else:
            report = analyze(read_lines(args.logfile), top_n=args.top, error_rate_threshold=args.error_threshold)
        print_console_report(report)

        out_path = Path(args.out)
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print()
        print(f"JSON report written to: {out_path.resolve()}")
        return 0
    except FileNotFoundError:
        print(f"Error: log file not found: {args.logfile}", file=sys.stderr)
        print("Tip: replace placeholder paths like 'path\\to\\access.log' with a real file path.", file=sys.stderr)
        print("Tip: try a quick run with: python .\\task2_log_analyzer\\log_analyzer.py --demo", file=sys.stderr)
        return 2
    except PermissionError:
        print(f"Error: permission denied reading: {args.logfile}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Cancelled.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
