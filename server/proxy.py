#! /usr/bin/env python3
from flask import Flask, request
import json
import requests

app = Flask(__name__)

@app.route('/<path>',methods=['POST'])
def post_op(path):
    data = request.get_json(force=True)
    try:
      data = requests.post('http://localhost:8089/%s' % path,json=data)
    except:
      return json.dumps({"status": "empty"}) 
    return data.text

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8088, debug=True, threaded=False)
