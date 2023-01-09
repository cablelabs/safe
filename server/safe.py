#! /usr/bin/env python3
import time
import os
import threading


class ProgressThread(threading.Thread):
  def __init__(self, safe):
    threading.Thread.__init__(self)
    self.safe = safe
    progress_timeout_env = os.getenv("PROGRESS_TIMEOUT")
    if progress_timeout_env is None or progress_timeout_env == "":
      self.interval = 30
    else:
      self.interval = float(progress_timeout_env)/2
  def run(self):
    while (True):
      self.safe.check_progress()
      time.sleep(self.interval)

class Safe:
  def __init__(self):
    self.nodes = {}
    self.aggregate = {}
    self.repost_aggregate = {}
    self.average = {}
    self.group_stats = {}
    self.registrations = {}

    should_debug_env = os.getenv("SHOULD_DEBUG")
    if should_debug_env is None or should_debug_env == "":
      self.should_debug = False
    else:
      self.should_debug = (should_debug_env == "yes")

    progress_timeout_env = os.getenv("PROGRESS_TIMEOUT")
    if progress_timeout_env is None or progress_timeout_env == "":
      progress_timeout = 60
    else:
      progress_timeout = float(progress_timeout_env)
    aggregation_timeout_env = os.getenv("AGGREGATION_TIMEOUT")
    if aggregation_timeout_env is None or aggregation_timeout_env == "":
      aggregation_timeout = 600
    else:
      aggregation_timeout = float(aggregation_timeout_env)
    poll_time_env = os.getenv("POLL_TIME")
    if poll_time_env is None or poll_time_env == "":
      poll_time = 10
    else:
      poll_time = float(poll_time_env)
    yield_time_env = os.getenv("YIELD_TIME")
    if yield_time_env is None or yield_time_env == "":
      yield_time = 0.005
    else:
      yield_time = float(yield_time_env)
    self.config = {}
    self.config["progress_timeout"] = progress_timeout
    self.config["aggregation_timeout"] = aggregation_timeout
    self.config["poll_time"] = poll_time
    self.config["yield_time"] = yield_time

    self.lock = threading.Semaphore()
    self.progress_thread = ProgressThread(self)
    self.progress_thread.start()

  def debug(self, msg):
    if not self.should_debug:
      return
    with open("controller.debug",'a') as f:
      f.write("SAFE DEBUG [%.3f] %s\n" % (time.time(),msg))

  def init_average(self, group, initiator=1):
    self.average[group] = {"status": "initiated", "time": time.time(), "initiator": initiator}
    self.group_stats[group] = {"posted":0,"skipped":0}
    if group in self.aggregate:
      del self.aggregate[group]

  def should_initiate(self, node, group=1):
    with self.lock:
      current_time = time.time()
      if not group in average: 
        self.init_average(group, node)
        return {"init": True}
      self.debug("Elapsed time: %.2f" % (current_time - self.average[group]["time"]))
      if (current_time - self.average[group]["time"]) > self.config["aggregation_timeout"]:
        self.init_average(group, node)
        return {"init": True}
      return {"init": False}

  def post_aggregate(self, from_node, to_node, aggregate, group=1):
    self.debug("post_aggregate: %s" % from_node)
    with self.lock:
      self.debug("Posting Aggregate: %s" % aggregate)
      if group in self.average and self.average[group]["initiator"] == from_node:
        self.init_average(group, from_node)
      elif group not in self.average:
        self.init_average(group, from_node)

      if not group in self.aggregate:
        self.aggregate[group] = {}
      self.aggregate[group][to_node] = {"aggregate": aggregate, "time": time.time(), "from_node": from_node}
      self.group_stats[group]["posted"] += 1
      if group not in self.repost_aggregate:
        self.repost_aggregate[group] = {}
      self.repost_aggregate[group][from_node] =  {"status": "consumed"}
      self.repost_aggregate[group][to_node] =  {"status": "empty"}
      return True 

  def internal_check_aggregate(self, params):
    node = params["node"]
    group = params["group"]
    result = {"status": "empty"}
    if group in self.repost_aggregate and node in self.repost_aggregate[group]:
      result = self.repost_aggregate[group][node] 
      del self.repost_aggregate[group][node]
    return result

  def poll_internal(self, func, params):
    TIMEOUT = self.config["poll_time"]
    WAIT_TIME = self.config["yield_time"]
    empty = True
    start_time =  time.time()
    with self.lock:
      result = func(params)
    empty =  ("status" in result) and (result["status"] == "empty")
    while empty and (time.time() - start_time) < TIMEOUT:
      time.sleep(WAIT_TIME)
      with self.lock:
        result = func(params)
        empty =  ("status" in result) and (result["status"] == "empty")
    return result

  def check_aggregate(self, node, group=1):
    return self.poll_internal(self.internal_check_aggregate, {"node": node, "group": group})

  def internal_get_aggregate(self, params):
    node = params["node"]
    group = params["group"]
    result = {"status": "empty"}
    if group in self.aggregate and node in self.aggregate[group]:
      result = {"status": "ok"}
      if "aggregate" in self.aggregate[group][node]:
        result["aggregate"] = self.aggregate[group][node]["aggregate"]
      if "from_node" in self.aggregate[group][node]:
        result["from_node"] = self.aggregate[group][node]["from_node"]
      del self.aggregate[group][node]
      result["posted"] = self.group_stats[group]["posted"] - self.group_stats[group]["skipped"] 
    return result

  def get_aggregate(self, node, group=1):
    self.debug("get_aggregate: %s" % node)
    return self.poll_internal(self.internal_get_aggregate, {"node": node, "group": group})

  def post_average(self, node, average, group=1):
    self.debug("post_average: %s" % node)
    with self.lock:
      self.average[group]["average"] = average
      self.average[group]["status"] = "posted"
      if group not in self.repost_aggregate:
        self.repost_aggregate[group] = {}
      if not node is None:
        self.repost_aggregate[group][node] =  {"status": "consumed"}
      return True

  def add(self, v1, v2, f):
    if not isinstance(v1, list):
      return (v1 + v2 * f)
    result = []
    for i in range(0,len(v1)):
      result.append(v1[i]+v2[i]*f)
    return result  

  def init_tot(self, v):
    if not isinstance(v, list):
      return 0
    return [ 0 for _ in range(len(v)) ]

  def divide(self, tot, n):
    if not isinstance(tot, list):
      return tot/n
    return list(map(lambda x: x/n,tot))

  def internal_get_average(self, params):
    num_groups = len(self.registrations)
    result = {"status": "empty"}
    tot = None
    n = 0
    num_avgs = 0
    for k in self.average.keys():
      if not "average" in self.average[k]:
        return {"status": "empty"}    
      if self.average[k]["status"] != "posted":
        continue
      if tot is None:
         tot = self.init_tot(self.average[k]["average"])
      tot = self.add(tot,self.average[k]["average"],self.group_stats[k]["posted"])
      n += self.group_stats[k]["posted"]
      num_avgs += 1
    if num_avgs >= num_groups:
      result = {"status": "ok"}
      result["average"] = self.divide(tot,n)
    return result

  def get_average(self, node=None):
    if not node is None:
      self.debug("get_average: %s" % node)
    result = self.poll_internal(self.internal_get_average, {"node": node})
    return result

  def check_progress(self):
    with self.lock:
      current_time = time.time()
      progress = []
      reposts = []
      for g in self.aggregate.keys():
       for n in self.aggregate[g].keys():
          elapsed = current_time - self.aggregate[g][n]["time"]  
          progress.append({"group": g, "node": n, "elapsed": elapsed}) 
          if elapsed > self.config["progress_timeout"]:
              reposts.append({"failed": n,"group":g,"node": self.aggregate[g][n]["from_node"], "repost": {"status": "repost", "repost_to": n+1}})

      for repost in reposts:
        if repost["group"] not in self.repost_aggregate:
          self.repost_aggregate[repost["group"]] = {}
        self.repost_aggregate[repost["group"]][repost["failed"]] = repost["repost"]
        del self.aggregate[repost["group"]][repost["failed"]]
        self.group_stats[repost["group"]]["skipped"] += 1
      return {"progress":progress,"stats": self.group_stats}

  def register(self, pub_key, group=1):
    with self.lock:
      self.debug("Pub Key: %s" % pub_key)
      if group not in self.registrations:
        self.registrations[group] = {}
      if pub_key in self.registrations[group]:
        return self.registrations[group][pub_key]
      current_index = len(self.registrations[group]) + 1
      self.registrations[group][pub_key] = {"index": current_index}
      return self.registrations[group][pub_key]

  def get_registrations(self, group=1):
    with self.lock:
      self.debug("Group: %s" % group)
      registration_map = {}
      if group not in self.registrations:
        return registration_map
      for key in self.registrations[group].keys():
        registration_map[self.registrations[group][key]["index"]] = {"pub_key": key}
      return registration_map

  def clear_data(self):
    with self.lock:
      self.nodes = {}
      self.aggregate = {}
      self.repost_aggregate = {}
      self.average = {}
      self.group_stats = {}
      self.registrations = {}
      return {"status":"OK"}
