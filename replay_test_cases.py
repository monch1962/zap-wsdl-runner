import os
import json
import requests
from glob import glob

test_case_dir = os.getenv("TEST_CASE_DIR", "/zap/output/test-cases")
parameter_file = os.getenv("PARAM_FILE", "/zap/output/test-params.json")
results_dir = os.getenv("RESULTS_DIR", "/zap/output/replay-results")
aggregate_file = os.path.join(results_dir, "summary.json")

# Load parameters
if os.path.exists(parameter_file):
    with open(parameter_file) as f:
        parameters = json.load(f)
else:
    parameters = {}

os.makedirs(results_dir, exist_ok=True)

def substitute(template, values):
    for key, value in values.items():
        template = template.replace(f"{{{{{key}}}}}", str(value))
    return template

summary = {
    "results": [],
    "errors": [],
    "passed": True
}

# Execute each test case
for file_path in sorted(glob(os.path.join(test_case_dir, "*.json"))):
    with open(file_path) as f:
        test = json.load(f)

    operation = test.get("operation")
    test_type = test.get("test_type")
    target_url = test.get("target_url")
    expected_status = test.get("expected_status", 200)
    body = substitute(test.get("sample_input", ""), parameters)

    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": operation
    }

    try:
        response = requests.post(target_url, data=body, headers=headers, timeout=10)
        result = {
            "operation": operation,
            "test_type": test_type,
            "status_code": response.status_code,
            "passed": response.status_code == expected_status,
            "response_excerpt": response.text[:500]
        }

        summary["results"].append(result)
        if not result["passed"]:
            summary["passed"] = False

        result_file = os.path.join(results_dir, f"{operation}_{test_type}.result.json")
        with open(result_file, "w") as rf:
            json.dump(result, rf, indent=2)

        status = "PASS" if result["passed"] else "FAIL"
        print(f"[{status}] {operation} ({test_type}) => {response.status_code}")

    except Exception as e:
        error = {
            "operation": operation,
            "test_type": test_type,
            "error": str(e)
        }
        summary["errors"].append(error)
        summary["passed"] = False

        error_file = os.path.join(results_dir, f"{operation}_{test_type}.error.json")
        with open(error_file, "w") as rf:
            json.dump(error, rf, indent=2)

        print(f"[ERROR] {operation} ({test_type}) => {str(e)}")

# Write aggregated summary
with open(aggregate_file, "w") as af:
    json.dump(summary, af, indent=2)

if not summary["passed"]:
    print("❌ One or more test cases failed or encountered errors.")
    exit(1)
else:
    print("✅ All test cases passed successfully.")