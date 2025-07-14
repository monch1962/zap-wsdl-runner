#!/usr/bin/env python3
import os
import json
from zeep import Client
from zeep.helpers import serialize_object

wsdl_path = os.getenv("WSDL_FILE")
target_url = os.getenv("TARGET_URL")
generate_http = os.getenv("GENERATE_HTTP", "false").lower() == "true"

if not wsdl_path or not target_url:
    raise ValueError("Both WSDL_FILE and TARGET_URL environment variables must be set.")

client = Client(wsdl=wsdl_path)

operations = []
cases = {}

output_dir = "/zap/output/test-cases"
os.makedirs(output_dir, exist_ok=True)

def generate_template_input(operation_name):
    try:
        template = client.get_type(f"ns0:{operation_name}Request")
        instance = template()
        return serialize_object(instance)
    except Exception:
        return f"<{operation_name}Request>...</{operation_name}Request>"

for service in client.wsdl.services.values():
    for port in service.ports.values():
        for op in port.binding._operations.values():
            operations.append(op.name)
            op_base = op.name.lower()
            cases[f"test_{op_base}_positive"] = {"operation": op.name, "type": "positive"}
            cases[f"test_{op_base}_negative"] = {"operation": op.name, "type": "negative"}

            # Generate templated XML input
            sample_input = generate_template_input(op.name)

            for test_type in ["positive", "negative"]:
                test_data = {
                    "operation": op.name,
                    "test_type": test_type,
                    "target_url": target_url,
                    "sample_input": sample_input
                }

                # Write JSON file
                json_path = os.path.join(output_dir, f"{op_base}_{test_type}.json")
                with open(json_path, "w") as f:
                    json.dump(test_data, f, indent=2)

                # Write HTTP file if enabled
                if generate_http:
                    http_path = os.path.join(output_dir, f"{op_base}_{test_type}.http")
                    with open(http_path, "w") as f:
                        f.write(f"POST {target_url} HTTP/1.1\n")
                        f.write("Content-Type: text/xml; charset=utf-8\n")
                        f.write(f"SOAPAction: "{op.name}"\n\n")
                        f.write(f"{sample_input}\n")

# Write summary test metadata for OPA
with open("/zap/opa/data/wsdl_operations.json", "w") as f:
    json.dump({"operations": operations}, f)

with open("/zap/opa/data/tested_operations.json", "w") as f:
    json.dump({"operations": operations, "cases": cases}, f)
