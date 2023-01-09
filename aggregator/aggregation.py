#! /usr/bin/python3
import rsa
import requests
import random
import time
import json
import base64
import msgpack
from bon import PracticalSecureAggregatorClient
import numpy as np
import message_encryption as me
import math


class TimeoutException(Exception):
  pass

class SecureAggregation:
  def __init__(self, options={}):
    """Initiates aggregator with options.

    Args:
    	options (dict): controller, precision, max_random, poll_time, aggregation_timeout,
             restart_wait, group, key_size, should_encrypt, ag_type (SAFE,BON,INSEC) 
    """ 
    self.options = options
    self.registrations = None
    if "controller" in self.options:
      self.controller = self.options["controller"]
    else:
       self.controller = "http://localhost:8088"
    if "precision" in self.options:
       self.precision = self.options["precision"]
    else:
       self.precision = 5
    if "max_random" in self.options:
       self.max_random = self.options["max_random"]
    else:
       self.max_random = 1000
    if "poll_time" in self.options:
      self.poll_time = self.options["poll_time"]
    else:
      self.poll_time = 0.01
    if "aggregation_timeout" in self.options:
      self.aggregation_timeout = self.options["aggregation_timeout"]
    else:
      self.aggregation_timeout = 10
    if "restart_wait" in self.options:
      self.restart_wait = self.options["restart_wait"]
    else:
      self.restart_wait = 10
    if "group" in self.options:
      self.group = self.options["group"]
    else:
      self.group = 1
    if "key_size" in self.options:
      self.key_size = self.options["key_size"]
    else:
      self.key_size = 1024
    if "should_encrypt" in self.options:
      self.should_encrypt = self.options["should_encrypt"]
    else:
      self.should_encrypt = True
    if "should_debug" in self.options:
      self.should_debug = self.options["should_debug"]
    else:
      self.should_debug = True
    if "real_index" in self.options:
      self.real_index = self.options["real_index"]
    else:
      self.real_index = random.randint(1,9999999)
    if "ag_type" in self.options:
      self.ag_type = self.options["ag_type"]
    else:
      self.ag_type = "SAFE"
    if "predicted_rate" in self.options:
      self.predicted_rate = self.options["predicted_rate"]
    else:
      self.predicted_rate = 0.2
    if "slowdown_factor" in self.options:
      self.slowdown_factor = self.options["slowdown_factor"]
    else:
      self.slowdown_factor = 1.7
    if "chunk_size" in self.options:
      self.chunk_size = self.options["chunk_size"]
    else:
      self.chunk_size = 25
    if "estimate_progress" in self.options:
      self.estimate_progress = self.options["estimate_progress"]
    else:
      self.estimate_progress = False
    if "basic_auth" in self.options:
      self.basic_auth = self.options["basic_auth"]
    else:
      self.basic_auth = False
    if "namespace" in self.options:
      self.namespace = self.options["namespace"]
    else:
      self.namespace = "global"
    if "namespace_password" in self.options:
      self.namespace_password = self.options["namespace_password"]
    else:
      self.namespace_password = ""

    self.pubkey = self.privkey = None

  def debug(self, msg):
    if self.should_debug:
      print("DEBUG: %s" % msg)

  def gen_key(self):
    (self.pubkey, self.privkey) = rsa.newkeys(self.key_size)
    return (self.pubkey, self.privkey)

  def set_key(self, pubkey, privkey):
    self.pubkey = pubkey
    self.privkey = privkey

  def register(self):
    """
    Registers aggregator with controller. All aggregators
    participating in an aggregation need to have called register
    before the aggregation start to get an index on the agggregation
    chain. The first aggregator to register becomes the
    initial initiator. After this call aggregator.index is set to the
    agggregator order on the chain.
    """
    if self.ag_type == "SAFE":
      if self.pubkey is None or self.privkey is None:
        (self.pubkey, self.privkey) = rsa.newkeys(self.key_size)
      pem = self.pubkey.save_pkcs1().decode("utf8")
      data = self.post("register",{"pub_key": pem})
      self.index = data["index"]
      self.initiator =  self.index == 1
    if self.ag_type == "BON":
      self.bon = PracticalSecureAggregatorClient(self.real_index)
      pub = self.bon.get_pubkey()
      data = self.post("register",{"pub_key": pub})
      self.index = data["index"]
      self.bon.id = self.index
      self.post("init_weights",{"node": self.index})
    if self.ag_type == "INSEC":
      data = self.post("register",{"pub_key": random.randint(1,999999999)})
      self.index = data["index"]

  def clear_data(self):
    self.post("clear_data",{})

  def post(self, path, val):    
    url = self.controller + "/" + path
    val["group"] = self.group
    val["namespace"] = self.namespace
    if self.basic_auth:
      data = requests.post(url, json = val, auth=(self.namespace,self.namespace_password))
    else:
      data = requests.post(url, json = val)
    try:
       j = json.loads(data.text)
    except Exception as e:
       print(data.text)
       raise(e)
    return j

  def get_random(self, n=1):
    return [ random.randint(1,self.max_random*10**self.precision)/(10**self.precision) for _ in range(n) ]

  def get_pubkey(self,i):
    return rsa.PublicKey.load_pkcs1(self.registrations["%d" % i]["pub_key"].encode("utf8")) 

  def to_bytes(self, val):
    return " ".join(map(lambda x: (("%." + ("%d" % self.precision) + "f") % x),val)).encode("utf8")

  def encrypt(self, val, enc_key):
    if self.should_encrypt:
      message_key = me.gen_key()
      encrypted_message_key = base64.b64encode(rsa.encrypt(message_key,enc_key)).decode("utf8")
      encrypted_message = base64.b64encode(me.encrypt(msgpack.packb(val,use_bin_type=True),message_key)).decode("utf8")
      return {'message':encrypted_message,'key':encrypted_message_key}
    else:
      return val

  def decrypt(self, val):
    if self.should_encrypt:
      message_key = rsa.decrypt(base64.b64decode(val['key']),self.privkey)
      return msgpack.unpackb(me.decrypt(base64.b64decode(val['message']),message_key),raw=False)
    else:
      return val

  def wait_for(self,path,indata={}):
     data = self.post(path, indata)
     while data["status"] == "empty":
       if time.time() - self.aggregation_start > self.aggregation_timeout:
         raise TimeoutException
       time.sleep(self.poll_time)
       if path == "get_average":
          self.predicted_wait_average()
       data = self.post(path, indata)
     return data

  def wait_for_repost(self, agg, target):
    data = self.wait_for("check_aggregate",{"node":target})
    if data["status"] == "repost":
      repost_to = ((data["repost_to"]-1) % self.n)+1 
      self.debug("Got repost to %d" % repost_to)
      enc_key = self.get_pubkey(repost_to)
      enc = self.encrypt(agg, enc_key)
      self.post("post_aggregate",{"from_node": self.index,"to_node": repost_to, "aggregate": enc})
      data = self.wait_for_repost(agg, repost_to)
      self.debug("aggregate failed to be consumed for node %d" % target)
    else:
      self.debug("aggregate consumed for node %d" % target)

  def initiate(self):
      data = self.post("should_initiate",{"node": self.index})
      if data["init"]:
        self.initiator = True
        self.debug("New initiator")

  def add(self,v1,v2):
    result = []
    for i in range(0,len(v1)):
      result.append(v1[i]+v2[i])
    return result

  def subtract(self,v1,v2,d=1):
    result = []
    for i in range(0,len(v1)):
      result.append((v1[i]-v2[i])/d)
    return result
  
  def weighted_aggregate(self, values, weight):
      """Allows computation of weighted aggregates.

      Args:
      	values (float[]): vector of features to be aggregated
      	weight (float): weight of this aggregator

      Returns:
      	The weighted average
      """ 
      aggregates = []
      aggregates.append(weight)
      for val in values:
        aggregates.append(val*weight)
      result = []
      averages = self.aggregate(aggregates)
      for i in range(1,len(averages)):
        result.append(averages[i]/averages[0])
      return result

  def insec_aggregate(self, v):
    result = self.post("update_model",{"node": self.real_index,"wait_for": self.n, "coef": v})
    if len(result["coef"]) == 1:
      return result["coef"][0]
    return result["coef"]


  def bon_aggregate(self, v):
    n = len(v)
    vals = []
    for val in v:
      vals.append([val])
    a = np.array(vals)
    self.bon.set_weights(np.zeros((n,1)) + a, (n,1))
    shared_keys = {}
    for k in self.registrations.keys():
      shared_keys[int(k)] = self.registrations[k]["pub_key"] 
    w = self.bon.set_sharedkeys(shared_keys)
    total = len(shared_keys)
    result = self.post("post_weights",{"node": self.index, "weights": list(w.flatten())})
    epoch = 0
    if result["post_secret"]:
      result = self.post("post_secret",{"node": self.index, "secret": [float(x) for x in list(self.bon.get_secret().flatten())]})
      epoch = result["epoch"]
    result = self.post("get_weights",{"wait_for": total,"epoch":epoch})
    while result["status"] == "empty":
      result = self.post("get_weights",{"wait_for": total,"epoch":epoch})
    # nodes failed
    if result["post_reveal_secret"]:
      failed_nodes = result["failed_nodes"]
      result = self.post("post_reveal_secret",{"node": self.index, "reveal_secret": [float(x) for x in list(self.bon.get_reveal_secret(failed_nodes).flatten())]})
      epoch = result["epoch"]
      result = self.post("get_weights",{"wait_for": total,"epoch":epoch})
      while result["status"] == "empty":
        result = self.post("get_weights",{"wait_for": total,"epoch":epoch})
    if len(result["weights"]) == 1:
      return result["weights"][0]
    return result["weights"]

    
  def refresh_registrations(self):
    self.registrations = self.post("registrations",{}) 
    self.n = len(self.registrations) 

  def predicted_wait_average(self):
    if not self.estimate_progress:
      return
    elapsed = time.time() - self.aggregation_start
    wait_left = max(0,self.predicted_average - elapsed)
    random_wait = random.random()
    time.sleep(wait_left + random_wait)

  def predicted_wait_aggregate(self):
    if not self.estimate_progress:
      return
    priority = math.ceil(self.index/self.chunk_size)
    max_priority = math.ceil(self.n/self.chunk_size)
    if self.initiator:
      priority = max_priority
    predicted_wake = priority**(self.slowdown_factor)*self.predicted_rate 
    self.predicted_average = max_priority**(self.slowdown_factor)*self.predicted_rate
    time.sleep(predicted_wake)

  def aggregate(self, v):
    """Aggregates float vectors across participants using the 
    SAFE, BON or INSEC algorithms depending on options set
    when creating the aggregator.

    Args:
    	v (float[]): vector of features to be aggregated

    Returns:
    	The average
    """ 
    if not isinstance(v, list):
      value = [v]
    else:
      value = v
    if self.registrations is None:
      self.refresh_registrations() 
    if self.ag_type == "BON":
      return self.bon_aggregate(value)
    if self.ag_type == "INSEC":
      return self.insec_aggregate(value)
    values = len(value)
    self.aggregation_start = time.time()
    self.next = (self.index % self.n)+1 
    enc_key = self.get_pubkey(self.next)
    try:
      if self.initiator:
        R = self.get_random(values)
        agg = self.add(R,value)
        enc = self.encrypt(agg,enc_key)
        self.post("post_aggregate",{"from_node": self.index,"to_node": self.next, "aggregate": enc})
        data = self.wait_for_repost(agg, self.next)
        self.predicted_wait_aggregate()
        data = self.wait_for("get_aggregate",{"node": self.index})
        dec = self.decrypt(data["aggregate"])
        avg = self.subtract(dec,R,data["posted"])
        self.post("post_average",{"average": avg, "node": self.index})
        self.predicted_wait_average()
        data = self.wait_for("get_average")
        avg = data["average"]
      else:
        self.predicted_wait_aggregate()
        data = self.wait_for("get_aggregate",{"node": self.index})
        dec = self.decrypt(data["aggregate"])
        agg = self.add(dec,value)
        enc = self.encrypt(agg,enc_key)
        self.debug("posting to node %d" % self.next)
        self.post("post_aggregate",{"from_node": self.index,"to_node": self.next, "aggregate": enc})
        data = self.wait_for_repost(agg, self.next)
        self.predicted_wait_average()
        data = self.wait_for("get_average")
        avg = data["average"]
    except TimeoutException:
      self.debug("Re-initiating aggregation with new initiator...")
      time.sleep(self.restart_wait)
      self.initiate()
      return self.aggregate(value)
    if len(value) == 1:
      return avg[0]
    return avg
