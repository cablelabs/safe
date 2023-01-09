#! /usr/bin/env python3
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os, getpass

namespaces = {}
filename = '/config/namespaces.json'
if os.path.exists(filename):
  with open(filename) as f:
    namespaces = json.loads(f.read())

namespace = input("Namespace:")
password = getpass.getpass("Password:")

namespaces[namespace] = generate_password_hash(password)

with open(filename,'w') as f:
  f.write(json.dumps(namespaces))
