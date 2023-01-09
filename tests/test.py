#! /usr/bin/env python3
from aggregation import SecureAggregation
import sys
import os
import json
from threading import Thread
import requests

class AggregationThread(Thread):
  def __init__(self, aggregator, val):
    super().__init__()
    self.aggregator = aggregator 
    self.val = val
  def run(self):
    self.result = self.aggregator.aggregate(self.val)

aggregation_vector = sys.argv[3:]
expected = float(sys.argv[2])
aggregation_type = sys.argv[1]

with open('/config/config.json') as f:
   options = json.loads(f.read())
options["controller"] = "http://localhost:8088"
options["ag_type"] = aggregation_type

threads = []
for v in aggregation_vector:
 secure_aggregator = SecureAggregation(options)
 secure_aggregator.register()
 print(f"INDEX {secure_aggregator.index}")
 threads.append(AggregationThread(secure_aggregator,float(v)))

sysexit = 0
for t in threads:
   t.start()
for t in threads:
   t.join()
   print(f"RESULT {t.result} EXPECTED {expected}")
   if t.result != expected:
     sysexit = 1

requests.post("http://localhost:8088/clear_data", json={})

if sysexit == 1:
  print(f"{aggregation_type} {expected} {aggregation_vector} TEST FAILED")
else:
  print(f"{aggregation_type} {expected} {aggregation_vector} TEST SUCCEEDED")

sys.exit(sysexit)
