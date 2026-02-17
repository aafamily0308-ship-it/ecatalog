import argparse
import json
from urllib import request


def get_json(url: str):
    with request.urlopen(url, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Check completion signals for Phase 1 and Phase 2")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    base = args.base_url
    checks = {}

    checks["phase1_products"] = isinstance(get_json(f"{base}/api/products"), list)
    checks["phase1_offers"] = isinstance(get_json(f"{base}/api/offers"), list)
    checks["phase1_diagnostics"] = "products_count" in get_json(f"{base}/api/diagnostics/summary")

    # Phase 2 endpoints availability checks (lightweight)
    checks["phase2_alerts_get"] = isinstance(get_json(f"{base}/api/alerts"), list)
    checks["phase2_fraud_get"] = isinstance(get_json(f"{base}/api/fraud-signals"), list)

    report = {
        "base_url": base,
        "checks": checks,
        "phase1_ok": all(checks[k] for k in ["phase1_products", "phase1_offers", "phase1_diagnostics"]),
        "phase2_ok": all(checks[k] for k in ["phase2_alerts_get", "phase2_fraud_get"]),
    }

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
