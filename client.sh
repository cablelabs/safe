#! /bin/bash
docker exec -it --env WEIGHT=$WEIGHT safe-aggregator python3 client.py $*
