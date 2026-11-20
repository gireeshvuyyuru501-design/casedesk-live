"""Evaluate the running server, using whichever intent mode it was started in."""
import argparse
import json
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--require-llm", action="store_true")
    args = parser.parse_args()
    base = f"http://127.0.0.1:{args.port}"

    def post(path, **data):
        return urlopen(Request(base + path, json.dumps(data).encode(),
                               {"Content-Type": "application/json"}), timeout=25)

    examples = [
        ("pending", "I was double-billed $84.50 at Harbor Cafe.", None, "explained", "SIM-01"),
        ("posted", "My statement shows two identical charges for 84.50.", None, "review", "SIM-02"),
        ("ambiguous", "I paid $84.50 and got charged twice.", None, "clarify", None),
        ("ambiguous", "I paid $84.50 and got charged twice.", "Cedar Market", "review", "SIM-02"),
        ("posted", "Can I update my email address?", None, "unsupported", None),
        ("posted", "I was charged twice.", None, "missing_amount", None),
        ("posted", "I was billed twice for $12.40.", None, "no_match", None),
    ]
    for scenario, message, merchant, expected, policy in examples:
        with post("/investigate", scenario=scenario, message=message, merchant=merchant) as response:
            events = [json.loads(line) for line in response]
        assert events[0]["kind"] == "progress", events
        assert events[-1]["kind"] == "result", events
        result = events[-1]["data"]
        assert result["status"] == expected, result
        assert result.get("policy", {}).get("id") == policy, result
        if args.require_llm:
            assert result["mode"] == "Groq LLM", result
        if expected == "clarify":
            assert result["options"] == ["Harbor Cafe", "Cedar Market"], result
        if merchant:
            assert {row["merchant"] for row in result["evidence"]} == {merchant}, result
        if expected == "review":
            with post("/review", case_id=result["case_id"], decision="approved") as response:
                assert json.load(response)["decision"] == "approved"
        print(f"PASS {scenario} -> {expected} ({result['mode']})")
    print(f"{len(examples)}/{len(examples)} checks passed")


if __name__ == "__main__":
    main()
