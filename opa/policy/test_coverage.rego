package zap.testcoverage

missing_coverage[op] {
  op := data.wsdl.operations[_]
  not data.tested.operations[_] == op
}

incomplete_test_type[op] {
  op := data.tested.operations[_]
  count({t | data.tested.cases[t].operation == op}) < 2
}

violation[msg] {
  op := missing_coverage[_]
  msg := sprintf("Missing test for operation: %s", [op])
}

violation[msg] {
  op := incomplete_test_type[_]
  msg := sprintf("Operation %s lacks both positive and negative tests", [op])
}