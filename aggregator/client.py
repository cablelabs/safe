#! /usr/bin/env python3
from aggregation import SecureAggregation
import sys
import os
import json

config_file = os.getenv("SAFE_CONFIG")
if config_file is None or config_file == "":
  config_file = "/config/config.json"

group_env = os.getenv("SAFE_GROUP")
if group_env is None or group_env == "":
  group = 1
else:
  group =int(group_env)


use_weight = os.getenv("WEIGHT") != None and os.getenv("WEIGHT") != ""
with open(config_file) as f:
   options = json.loads(f.read())
options["group"] = group
s = SecureAggregation(options)
if len(sys.argv) > 1 and sys.argv[1] == "clear":
  s.clear_data()
  sys.exit(0)
s.register()
print(s.index)
agg = input("Aggregate: ") 
if use_weight:
  weight = int(os.getenv("WEIGHT"))
while agg != "":
  v = list(map(lambda x: float(x),agg.split(" ")))
  if not use_weight:
    val = s.aggregate(v)
  else:
    val = s.weighted_aggregate(v, weight)

  if isinstance(val, list):
    valout = " ".join(map(lambda x: "%.5f" % x,val))
  else:
    valout = "%.5f" % val
  print("Average: %s" % valout)
  agg = input("Aggregate: ") 
