import argparse
import json
from pathlib import Path
from urllib import request, error


def fetch_json(url: str) -> dict:
    with request.urlopen(url, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def tail_file(path: Path, lines: int = 80) -> list[str]:
    if not path.exists():
        return [f"Log file not found: {path}"]
    content = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    return content[-lines:]


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect eCatalog remote diagnostics")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Server base URL")
    parser.add_argument("--log-file", default="ecatalog.log", help="Path to log file")
    parser.add_argument("--output", default="diagnostics_report.json", help="Output JSON path")
    args = parser.parse_args()

    report: dict = {"base_url": args.base_url}

    try:
        report["health"] = fetch_json(f"{args.base_url}/health")
    except Exception as exc:  # network/runtime boundary
        report["health_error"] = str(exc)

    try:
        report["diagnostics"] = fetch_json(f"{args.base_url}/api/diagnostics/summary")
    except error.HTTPError as exc:
        report["diagnostics_error"] = f"HTTP {exc.code}"
    except Exception as exc:
        report["diagnostics_error"] = str(exc)

    report["log_tail"] = tail_file(Path(args.log_file), lines=120)

    output = Path(args.output)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Diagnostics saved to {output}")


if __name__ == "__main__":
    main()
