#! /usr/bin/env python3
import time
import os
import threading
import numpy as np

class Bon:
  def __init__(self):
    self.nodes = {}
    progress_timeout_env = os.getenv("PROGRESS_TIMEOUT")
    if progress_timeout_env is None or progress_timeout_env == "":
      progress_timeout = 60
    else:
      progress_timeout = float(progress_timeout_env)
    self.config = {}
    self.config["progress_timeout"] = progress_timeout
    should_debug_env = os.getenv("SHOULD_DEBUG")
    if should_debug_env is None or should_debug_env == "":
      self.should_debug = False
    else:
      self.should_debug = (should_debug_env == "yes")
    self.lock = threading.Semaphore()

  def debug(self, msg):
    if not self.should_debug:
      return
    with open("controller.debug",'a') as f:
      f.write("BON DEBUG [%.3f] %s\n" % (time.time(),msg))

  def get_secure_posted(self, epoch):
    posted = 0
    reveal_posted = 0
    with self.lock:
      for n in self.nodes.keys():
        if self.nodes[n]["epoch"] == epoch and self.nodes[n]["secret_epoch"] == epoch:
          posted += 1
        if self.nodes[n]["epoch"] == epoch and self.nodes[n]["reveal_secret_epoch"] == epoch:
          reveal_posted += 1
    return (posted,reveal_posted)

  def get_failed_nodes(self, epoch):
    failed_nodes = []
    with self.lock:
      for n in self.nodes.keys():
        if self.nodes[n]["epoch"] != epoch or self.nodes[n]["secret_epoch"] != epoch:
          failed_nodes.append(n)
    return failed_nodes

  def wait_for_secure(self, total_nodes, epoch):
    start_time = time.time()
    (posted, reveal_posted) = self.get_secure_posted(epoch)
    while posted < total_nodes and (time.time() - start_time) < self.config["progress_timeout"]:
      (posted, reveal_posted) = self.get_secure_posted(epoch)
      failed_nodes = total_nodes - posted
      # for now only handle a single failure at a time
      if reveal_posted == (total_nodes - failed_nodes):
        posted = total_nodes
        break
      time.sleep(0.01)
    return {"ok": posted >= total_nodes,"timeout":  (time.time() - start_time) >= self.config["progress_timeout"]}

  def init_weights(self, node):
    with self.lock:
      if node not in self.nodes:
         self.nodes[node] = {"epoch": 0, "secret_epoch": 0, "reveal_secret_epoch": 0}
    return {"status": "OK"}

  def post_weights(self, node, weights):
    with self.lock:
      if node not in self.nodes:
         self.nodes[node] = {"epoch": 0, "secret_epoch": 0, "reveal_secret_epoch": 0}
      self.nodes[node]["weights"] = weights
      self.nodes[node]["epoch"] += 1
    return {"post_secret": True}

  def post_secret(self, node, secret):
    with self.lock:
      self.nodes[node]["secret"] = secret
      self.nodes[node]["secret_epoch"] += 1
    return {"status": "OK","epoch": self.nodes[node]["epoch"]}

  def post_reveal_secret(self, node, reveal_secret):
    with self.lock:
      self.nodes[node]["reveal_secret"] = reveal_secret
      self.nodes[node]["reveal_secret_epoch"] += 1
    return {"status": "OK","epoch": self.nodes[node]["epoch"]}

  def get_weights(self, total_nodes, epoch):
    is_ok = self.wait_for_secure(total_nodes,epoch)
    if is_ok["timeout"]:
      failed_nodes = self.get_failed_nodes(epoch)
      return {"status": "failure", "post_reveal_secret": True, "failed_nodes": failed_nodes}
    if not is_ok["ok"]:
      return {"status": "empty"}
    with self.lock:
      n = len(list(self.nodes.values())[0]["weights"])
      agg =  np.zeros((n,1))
      for node in self.nodes.values():
        if node["epoch"] == epoch and node["secret_epoch"] == epoch:
          self.debug("weights: %s" % (node["weights"]))
          self.debug("secret: %s" % (node["secret"]))
          agg += np.array(node["weights"]).reshape(n,1)
          agg += np.array(node["secret"]).reshape(n,1)
          if node["reveal_secret_epoch"] == epoch:
            self.debug("reveal secret: %s" % (node["reveal_secret"]))
            agg += np.array(node["reveal_secret"]).reshape(n,1)
    return {"status": "OK","post_reveal_secret": False, "weights": list(agg.flatten())}

  def clear_data(self):
    with self.lock:
      self.nodes = {}
      return {"status":"OK"}
