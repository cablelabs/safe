#! /bin/bash
python3 -u  /usr/local/bin/pdoc --http 0.0.0.0:9099 /aggregator/aggregation.py > pdoc.log 2>&1 &
touch pdoc.log
touch aggregator.log
tail -f aggregator.log -f pdoc.log
