#! /bin/bash
docker exec -it safe-controller python3 add_namespace.py $*
docker exec -it safe-controller touch controller.py
