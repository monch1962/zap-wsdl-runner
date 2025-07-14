#!/bin/bash
set -e

: "${TARGET_URL:?Environment variable TARGET_URL is required}"
: "${WSDL_PATH:=/zap/wsdls}"
: "${OUTPUT_PATH:=/zap/output}"
: "${SCAN_TYPE:=baseline}"
: "${NTFY_TOPIC:=}"
: "${NTFY_URL:=https://ntfy.sh}"
: "${SCAN_TIMEOUT:=600}"
: "${ZAP_ADDON_PATH:=}"

echo "Running ZAP WSDL scan against $TARGET_URL"
echo "Looking for WSDLs in $WSDL_PATH"
echo "Output will be saved to $OUTPUT_PATH"
echo "Scan type: $SCAN_TYPE with timeout $SCAN_TIMEOUT seconds"

mkdir -p "$OUTPUT_PATH"

# Install ZAP add-ons if provided
if [ -n "$ZAP_ADDON_PATH" ] && [ -d "$ZAP_ADDON_PATH" ]; then
  echo "Installing ZAP add-ons from $ZAP_ADDON_PATH"
  for addon in "$ZAP_ADDON_PATH"/*.zap "$ZAP_ADDON_PATH"/*.addon; do
    if [ -f "$addon" ]; then
      echo "Installing add-on: $addon"
      cp "$addon" /home/zap/.ZAP/plugin/
    fi
  done
fi

for wsdl in "$WSDL_PATH"/*.wsdl; do
  echo "Generating test cases from: $wsdl"
  WSDL_FILE="$wsdl" TARGET_URL="$TARGET_URL" python3 /zap/generate_tests_from_wsdl.py
done

SCAN_CMD="zap-baseline.py -t $TARGET_URL -r $OUTPUT_PATH/zap-report.html"
if [ "$SCAN_TYPE" == "full" ]; then
  SCAN_CMD="zap-full-scan.py -t $TARGET_URL -r $OUTPUT_PATH/zap-full-report.html"
fi

echo "Running scan: $SCAN_CMD"
timeout "$SCAN_TIMEOUT" bash -c "$SCAN_CMD"

echo "Validating coverage with OPA..."
opa eval --format pretty \
  --data /zap/opa/policy/test_coverage.rego \
  --data /zap/opa/data/wsdl_operations.json \
  --data /zap/opa/data/tested_operations.json \
  'data.zap.testcoverage.violation' | tee "$OUTPUT_PATH/opa-validation.txt"

VIOLATION_COUNT=$(opa eval --format raw -q 'count(data.zap.testcoverage.violation)' \
  --data /zap/opa/policy/test_coverage.rego \
  --data /zap/opa/data/wsdl_operations.json \
  --data /zap/opa/data/tested_operations.json)

if [ "$VIOLATION_COUNT" -ne 0 ]; then
  echo "OPA policy violations found."
  if [ -n "$NTFY_TOPIC" ]; then
    curl -H "Title: ZAP Test Failed" -H "Priority: urgent" \
      -d "ZAP/OPA policy check failed for $TARGET_URL" \
      "$NTFY_URL/$NTFY_TOPIC"
  fi
  exit 1
else
  echo "OPA policy validation passed."
  if [ -n "$NTFY_TOPIC" ]; then
    curl -H "Title: ZAP Test Passed" -H "Priority: default" \
      -d "ZAP tests passed successfully for $TARGET_URL" \
      "$NTFY_URL/$NTFY_TOPIC"
  fi
fi