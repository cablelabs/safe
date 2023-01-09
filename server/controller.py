#! /usr/bin/env python3
from flask import Flask, request, jsonify, Response, abort
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import check_password_hash
from flasgger import Swagger
from functools import wraps
import json
import sys
import os

from insec import InSec
from safe import Safe
from bons import Bon


app = Flask(__name__)
app.config['SWAGGER'] = {
    'title': 'SAFE API',
}

swagger = Swagger(app,template_file='swagger.yaml')

auth = HTTPBasicAuth()

ns = {} 

namespace_auth_db = {}
filename = '/config/namespaces.json'
if os.path.exists(filename):
  with open(filename) as f: 
    namespace_auth_db = json.loads(f.read())

auth_enabled_env = os.getenv("AUTH_ENABLED")
auth_enabled = False
if not auth_enabled_env is None and auth_enabled_env == "yes":
  auth_enabled = True

print(f"Auth Enabled {auth_enabled}")

@auth.verify_password
def verify_password(namespace, password):
  if namespace in namespace_auth_db and \
            check_password_hash(namespace_auth_db.get(namespace), password):
        return namespace

@auth.login_required
def check_user(user):
  auth_user = auth.current_user() 
  if auth_user != user:
    abort(401)

def get_instance_namespace(namespace, algo, constructor):
  global ns
  if namespace not in ns:
    ns[namespace] = {}
  if algo not in ns[namespace]:
    ns[namespace][algo] = constructor()
  return ns[namespace][algo]

def get_instance(namespace, algo, constructor):
  global auth_enabled
  if auth_enabled:
    response = check_user(namespace)
    if isinstance(response, Response):
      abort(401)
  return get_instance_namespace(namespace, algo, constructor)

def get_insec(namespace="global"):
  return get_instance(namespace, "insec", InSec)
  
def get_bon(namespace="global"):
  return get_instance(namespace, "bon", Bon)

def get_safe(namespace="global"):
  return get_instance(namespace, "safe", Safe)

def get_ns(data):
  if "namespace" in data:
    return data["namespace"]
  return "global"

@app.route('/update_model',methods=['POST'])
def update_model():
    """Allows a set of nodes to average coefficients.
    ---
    tags:
      - insec
    parameters:
      - name: payload
        in: body
        example:
          namespace: global
          node: 1
          coef: [1.0]
          wait_for: 3
        properties:
          namespace:
            type: string
          node:
            type: integer
          coef:
            type: array
            items:
              type: number
              format: float
          wait_for:
            type: integer
    responses:
      200:
       description: Averages across all submitted coefficicents 
    security:
        - basic: []
    """
    data = request.get_json(force=True)
    total_nodes = data["wait_for"]
    node = data["node"]
    coef = data["coef"]
    return json.dumps(get_insec(get_ns(data)).update_model(node, coef, total_nodes))

@app.route('/init_weights',methods=['POST'])
def init_weights():
    """Initiate weights for a node.
    ---
    tags:
      - bon
    parameters:
      - name: payload
        in: body
        example:
          namespace: global
          node: 1
        properties:
          namespace:
            type: string
          node:
            type: integer
    responses:
      200:
       description: status whether OK
    security:
        - basic: []
    """
    data = request.get_json(force=True)
    node = data["node"]
    return json.dumps(get_bon(get_ns(data)).init_weights(node))

@app.route('/post_weights',methods=['POST'])
def post_weights():
    """Submit weights for a node.
    ---
    tags:
      - bon
    parameters:
      - name: payload
        in: body
        example:
          namespace: global
          node: 1
          weights: [1.0]
        properties:
          namespace:
            type: string
          node:
            type: integer
          weights:
            type: array
            items:
              type: number
              format: float
    responses:
      200:
       description: post_secret whether secret should be posted
    security:
        - basic: []
    """
    data = request.get_json(force=True)
    node = data["node"]
    weights = data["weights"]
    return json.dumps(get_bon(get_ns(data)).post_weights(node, weights))

@app.route('/post_secret',methods=['POST'])
def post_secret():
    """Submit secret for a node.
    ---
    tags:
      - bon
    parameters:
      - name: payload
        in: body
        example:
          namespace: global
          node: 1
          secret: [1.0]
        properties:
          namespace:
            type: string
          node:
            type: integer
          secret:
            type: array
            items:
              type: number
              format: float
    responses:
      200:
       description: status whether OK, epoch current epoch
    security:
        - basic: []
    """
    data = request.get_json(force=True)
    node = data["node"]
    secret = data["secret"]
    return json.dumps(get_bon(get_ns(data)).post_secret(node, secret))

@app.route('/post_reveal_secret',methods=['POST'])
def post_reveal_secret():
    """Submit reveal secret for a node during recovery.
    ---
    tags:
      - bon
    parameters:
      - name: payload
        in: body
        example:
          namespace: global
          node: 1
          reveal_secret: [1.0]
        properties:
          namespace:
            type: string
          node:
            type: integer
          reveal_secret:
            type: array
            items:
              type: number
              format: float
    responses:
      200:
       description: status whether OK, epoch current epoch
    security:
        - basic: []
    """
    data = request.get_json(force=True)
    node = data["node"]
    reveal_secret = data["reveal_secret"]
    return json.dumps(get_bon(get_ns(data)).post_reveal_secret(node, reveal_secret))

@app.route('/get_weights',methods=['POST'])
def get_weights():
    """Retrieve weights for epoch and wait for specified number of submissions.
    ---
    tags:
      - bon
    parameters:
      - name: payload
        in: body
        example:
          namespace: global
          wait_for: 3
          epoch: 1
        properties:
          namespace:
            type: string
          wait_for:
            type: integer
          epoch:
            type: integer
    responses:
      200:
       description: status whether OK, post_reveal_secret, weights
    security:
        - basic: []
    """
    data = request.get_json(force=True)
    total_nodes = data["wait_for"]
    epoch = data["epoch"]
    return json.dumps(get_bon(get_ns(data)).get_weights(total_nodes, epoch))

@app.route('/should_initiate',methods=['POST'])
def should_initiate():
    """Called by all nodes during initiator failure to select a new initiator.
    ---
    tags:
      - safe
    parameters:
      - name: payload
        in: body
        example:
          namespace: global
          node: 1
          group: 1
        properties:
          namespace:
            type: string
          node:
            type: integer
          group:
            type: integer
    responses:
      200:
       description: init whether node was selected initiator
    security:
        - basic: []
    """
    data = request.get_json(force=True)
    node = data["node"]
    group = 1
    if "group" in data:
      group = data["group"]
    return json.dumps(get_safe(get_ns(data)).should_initiate(node, group))

@app.route('/post_aggregate',methods=['POST'])
def post_aggregate():
    """Called by all nodes during initiator failure to select a new initiator. Aggregate is encrypted
       with to_node public key if encryption is on.
    ---
    tags:
      - safe
    parameters:
      - name: payload
        in: body
        example:
          namespace: global
          from_node: 1
          to_node: 2
          group: 1
          aggregate: agg
        properties:
          namespace:
            type: string
          from_node:
            type: integer
          to_node:
            type: integer
          group:
            type: integer
          aggregate:
            type: string
    responses:
      200:
       description: data input
    security:
        - basic: []
    """
    data = request.get_json(force=True)
    from_node = data["from_node"]
    to_node = data["to_node"]
    group = 1
    if "group" in data:
      group = data["group"]
    aggregate = data["aggregate"]
    get_safe(get_ns(data)).post_aggregate(from_node, to_node, aggregate, group)
    return json.dumps(data)

@app.route('/check_aggregate',methods=['POST'])
def check_aggregate():
    """Check whether a target has concumed an aggregate.
    ---
    tags:
      - safe
    parameters:
      - name: payload
        in: body
        example:
          namespace: global
          node: 1
          group: 1
        properties:
          namespace:
            type: string
          node:
            type: integer
          group:
            type: integer
    responses:
      200:
       description: whether consumed or to repost
    security:
        - basic: []
    """
    data = request.get_json(force=True)
    node = data["node"]
    group = 1
    if "group" in data:
      group = data["group"]
    return json.dumps(get_safe(get_ns(data)).check_aggregate(node, group))

@app.route('/get_aggregate',methods=['POST'])
def get_aggregate():
    """Retrieve an aggregate for a target node.
    ---
    tags:
      - safe
    parameters:
      - name: payload
        in: body
        example:
          namespace: global
          node: 1
          group: 1
        properties:
          namespace:
            type: string
          node:
            type: integer
          group:
            type: integer
    responses:
      200:
       description: aggregate and posted stats
    security:
        - basic: []
    """
    data = request.get_json(force=True)
    node = data["node"]
    group = 1
    if "group" in data:
      group = data["group"]
    return json.dumps(get_safe(get_ns(data)).get_aggregate(node, group))

@app.route('/post_average',methods=['POST'])
def post_average():
    """Broadcast an avarage. Computes global average across groups.
    ---
    tags:
      - safe
    parameters:
      - name: payload
        in: body
        example:
          namespace: global
          node: 1
          group: 1
          average: [1.0]
        properties:
          namespace:
            type: string
          node:
            type: integer
          group:
            type: integer
          average:
            type: array
            items:
              type: number
              format: float
    responses:
      200:
       description: data input
    security:
        - basic: []
    """
    data = request.get_json(force=True)
    node  = None
    if "node" in data:
      node = data["node"]
    group = 1
    if "group" in data:
      group = data["group"]
    average = data["average"]
    get_safe(get_ns(data)).post_average(node, average, group)
    return json.dumps(data)

@app.route('/get_average',methods=['POST'])
def get_average():
    """Receive an avarage.
    ---
    tags:
      - safe
    parameters:
      - name: payload
        in: body
        example:
          namespace: global
          node: 1
        properties:
          namespace:
            type: string
          node:
            type: integer
    responses:
      200:
       description: average
    security:
        - basic: []
    """
    data = request.get_json(force=True)
    node = None
    if "node" in data:
      node = data["node"]
    return json.dumps(get_safe(get_ns(data)).get_average(node))

@app.route('/register',methods=['POST'])
def register():
    """Register public key and obtain chain index.
    ---
    tags:
      - safe
    parameters:
      - name: payload
        in: body
        example:
          namespace: global
          pub_key: pub_key
        properties:
          namespace:
            type: string
          pub_key:
            type: string
    responses:
      200:
       description: index
    security:
        - basic: []
    """
    data = request.get_json(force=True)
    pub_key = data["pub_key"]
    return json.dumps(get_safe(get_ns(data)).register(pub_key))

@app.route('/registrations',methods=['POST'])
def get_registrations():
    """Receive registrations.
    ---
    tags:
      - safe
    parameters:
      - name: payload
        in: body
        example:
          namespace: global
          group: 1
        properties:
          namespace:
            type: string
          group:
            type: integer
    responses:
      200:
       description: public keys and indexes of participants
    security:
        - basic: []
    """
    data = request.get_json(force=True)
    group = 1
    if "group" in data:
      group = data["group"]
    return json.dumps(get_safe(get_ns(data)).get_registrations(group))

@app.route('/clear_data',methods=['POST'])
def clear_data():
  data = request.get_json(force=True)
  get_safe(get_ns(data)).clear_data()
  get_bon(get_ns(data)).clear_data()
  get_insec(get_ns(data)).clear_data()
  return json.dumps({"status":"OK"})


if __name__ == "__main__":
    port = 8088
    if len(sys.argv) > 1:
       port = int(sys.argv[1])
    app.run(host="0.0.0.0", port=port, debug=True, threaded=True)
