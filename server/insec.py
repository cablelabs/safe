#! /usr/bin/env python3
import time
import os
import threading

class InSec:
  def __init__(self):
    self.nodes = {}
    self.lock = threading.Semaphore()
   
    should_debug_env = os.getenv("SHOULD_DEBUG")
    if should_debug_env is None or should_debug_env == "":
      self.should_debug = False
    else:
      self.should_debug = (should_debug_env == "yes")

  def debug(self, msg):
    if not self.should_debug:
      return
    with open("controller.debug",'a') as f:
      f.write("INSEC DEBUG [%.3f] %s\n" % (time.time(),msg))

  def get_avg(self):
    avg = {}
    n = len(self.nodes)
    for node in self.nodes.keys():
      if not "coef" in avg:
        avg["coef"] = [0]*len(self.nodes[node]["coef"])
      for i in range(0,len(self.nodes[node]["coef"])):
        avg["coef"][i] += self.nodes[node]["coef"][i]
    for i in range(0, len(avg["coef"])):
      avg["coef"][i] = avg["coef"][i]/n
    return avg 

  def get_posted(self, epoch):
    posted = 0
    with self.lock:
      for n in self.nodes.keys():
        if self.nodes[n]["epoch"] == epoch:
          posted += 1
    return posted

  def wait_for(self, total_nodes, epoch):
    posted = self.get_posted(epoch)
    while posted < total_nodes:
      posted = self.get_posted(epoch)
      time.sleep(0.01)

  def update_model(self, node, coef, total_nodes):
    self.debug("Node %d posting and waiting for %d updates" % (node, total_nodes))
    with self.lock:
      if node not in self.nodes:
         self.nodes[node] = {"epoch": 0}
      self.nodes[node]["coef"] = coef
      self.nodes[node]["epoch"] += 1
    self.debug("Node %d waiting for %d updates in epoch %d" % (node, total_nodes, self.nodes[node]["epoch"]))
    self.wait_for(total_nodes,self.nodes[node]["epoch"]) 
    with self.lock:
      avg = self.get_avg()
    self.debug("Data: %s" % avg)
    return avg

  def clear_data(self):
    with self.lock:
      self.nodes = {}
      return {"status":"OK"}
