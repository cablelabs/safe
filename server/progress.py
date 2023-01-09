#! /usr/bin/env python3

import requests
import os
import time
import json
import sys

progress_timeout_env = os.getenv("PROGRESS_TIMEOUT")
if progress_timeout_env is None or progress_timeout_env == "":
  progress_timeout = 60
else:
  progress_timeout = float(progress_timeout_env)

if progress_timeout == 0:
  sys.exit(0)

while 1:
  try:  
    time.sleep(progress_timeout/2)
    data = requests.post("http://localhost:8088/check_progress",json={})
  except:
     pass

