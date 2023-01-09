#! /usr/bin/python3
from random import randrange
import numpy as np
from copy import deepcopy
import codecs
import pickle
import json
import sys

"""
Adapted from https://github.com/ammartahir24/SecureAggregation
"""

class PracticalSecureAggregator:
	def __init__(self,common_base,common_mod,dimensions,weights):
		self.secretkey = randrange(common_mod)
		self.base = common_base
		self.mod = common_mod
		self.pubkey = (self.base**self.secretkey) % self.mod
		self.sndkey = randrange(common_mod)
		self.dim = dimensions
		self.weights = weights
		self.keys = {}
		self.id = ''
	def public_key(self):
		return self.pubkey
	def set_weights(self,wghts,dims):
		self.weights = wghts
		self.dim = dims
	def configure(self,base,mod):
		self.base = base
		self.mod = mod
		self.pubkey = (self.base**self.secretkey) % self.mod
	def generate_weights(self,seed):
		np.random.seed(seed)
		return np.float32(np.random.rand(self.dim[0],self.dim[1]))
	def prepare_weights(self,shared_keys,myid):
		self.keys = shared_keys
		self.id = myid
		wghts = deepcopy(self.weights)
		for sid in shared_keys:
			if sid>myid:
				#print ("1",myid,sid,(shared_keys[sid]**self.secretkey)%self.mod)
				wghts+=self.generate_weights((shared_keys[sid]**self.secretkey)%self.mod)
			elif sid<myid:
				#print ("2",myid,sid,(shared_keys[sid]**self.secretkey)%self.mod)
				wghts-=self.generate_weights((shared_keys[sid]**self.secretkey)%self.mod)
		wghts+=self.generate_weights(self.sndkey)
		return wghts
	def reveal(self, keylist):
		wghts = np.zeros(self.dim)
		for each in keylist:
			#print(each)
			if each<self.id:
				wghts-=self.generate_weights((self.keys[each]**self.secretkey)%self.mod)
			elif each>self.id:
				wghts+=self.generate_weights((self.keys[each]**self.secretkey)%self.mod)
		return -1*wghts
	def private_secret(self):
		return self.generate_weights(self.sndkey)


class PracticalSecureAggregatorClient:
	def __init__(self, node_id):
		self.aggregator = PracticalSecureAggregator(3,100103,(10,1),np.float32(np.full((10,1),3,dtype=int)))
		self.id = node_id
		self.keys = {}
                
	def configure(self,b,m):
		self.aggregator.configure(b,m)

	def set_weights(self,wghts,dims):
		self.aggregator.set_weights(wghts,dims)

	def get_pubkey(self):
		return self.aggregator.public_key()

	def get_weights(self):
		return self.aggregator.prepare_weights(self.keys,self.id)

	def set_sharedkeys(self,keydict):
		self.keys = keydict
		return self.aggregator.prepare_weights(self.keys,self.id)

	def get_secret(self):
		return -1*self.aggregator.private_secret()

	def get_reveal_secret(self,keylist):
		return self.aggregator.reveal(keylist)

if __name__ == "__main__":

  print(np.zeros((10,1)))
  a1 = np.array([[1],[2],[3],[4],[5],[6],[7],[8],[9],[10]])
  a2 = np.array([[11],[12],[13],[14],[15],[16],[17],[18],[19],[20]])
  a3 = np.array([[10],[10],[10],[10],[10],[10],[10],[10],[10],[10]])

  s1 = PracticalSecureAggregatorClient(1)
  s1.set_weights(np.zeros((10,1)) + a1, (10,1))
  s2 = PracticalSecureAggregatorClient(2)
  s2.set_weights(np.zeros((10,1)) + a2,(10,1))
  s3 = PracticalSecureAggregatorClient(3)
  s3.set_weights(np.zeros((10,1))+ a3,(10,1))
  
  p1 = s1.get_pubkey()
  p2 = s2.get_pubkey()
  p3 = s3.get_pubkey()
 
  keys = {} 
  keys[1] = p1
  keys[2] = p2
  keys[3] = p3

  w1 = s1.set_sharedkeys(keys)
  w2 = s2.set_sharedkeys(keys)
  w3 = s3.set_sharedkeys(keys)

  # s1+s2 w s3 failing
  aggregate = np.zeros((10,1))

  aggregate += w1
  aggregate += w2
  
  sec1 = s1.get_secret()
  sec2 = s2.get_secret()

  aggregate += sec1
  aggregate += sec2

  r1 = s1.get_reveal_secret([3])
  r2 = s2.get_reveal_secret([3])

  aggregate += r1
  aggregate += r2

  print("FINAL WEIGHTS 1:", aggregate)
  
  # s1+s2+s3 all ok
  aggregate = np.zeros((10,1))

  aggregate += w1
  aggregate += w2
  aggregate += w3

  sec1 = s1.get_secret()
  sec2 = s2.get_secret()
  sec3 = s3.get_secret()

  aggregate += sec1
  aggregate += sec2
  aggregate += sec3
  
  print("FINAL WEIGHTS 2:", aggregate)

  # update
  aggregate = np.zeros((10,1))

  a1 = np.array([[2],[4],[6],[8],[10],[12],[14],[16],[18],[20]])
  a2 = np.array([[22],[24],[26],[28],[30],[32],[34],[36],[38],[40]])
  a3 = np.array([[20],[20],[20],[20],[20],[20],[20],[20],[20],[20]])

  s1.set_weights(np.zeros((10,1)) + a1, (10,1))
  s2.set_weights(np.zeros((10,1)) + a2, (10,1))
  s3.set_weights(np.zeros((10,1)) + a3, (10,1))

  w1 = s1.get_weights()
  w2 = s2.get_weights()
  w3 = s3.get_weights()

  aggregate += w1
  aggregate += w2
  aggregate += w3

  sec1 = s1.get_secret()
  sec2 = s2.get_secret()
  sec3 = s3.get_secret()

  aggregate += sec1
  aggregate += sec2
  aggregate += sec3

  print("FINAL WEIGHTS 3:", aggregate)


  # s1+s2+s4 w s3 failing
  aggregate = np.zeros((10,1))
  s1 = PracticalSecureAggregatorClient(1)
  s2 = PracticalSecureAggregatorClient(2)
  s3 = PracticalSecureAggregatorClient(3)
  s4 = PracticalSecureAggregatorClient(4)

  p1 = s1.get_pubkey()
  p2 = s2.get_pubkey()
  p3 = s3.get_pubkey()
  p4 = s4.get_pubkey()
 
  keys = {} 
  keys[1] = p1
  keys[2] = p2
  keys[3] = p3
  keys[4] = p4

  w1 = s1.set_sharedkeys(keys)
  w2 = s2.set_sharedkeys(keys)
  w3 = s3.set_sharedkeys(keys)
  w4 = s4.set_sharedkeys(keys)


  a1 = np.array([[2],[4],[6],[8],[10],[12],[14],[16],[18],[20]])
  a2 = np.array([[22],[24],[26],[28],[30],[32],[34],[36],[38],[40]])
  a3 = np.array([[20],[20],[20],[20],[20],[20],[20],[20],[20],[20]])
  a4 = np.array([[40],[40],[40],[40],[40],[40],[40],[40],[40],[40]])


  s1.set_weights(np.zeros((10,1)) + a1, (10,1))
  s2.set_weights(np.zeros((10,1)) + a2, (10,1))
  s3.set_weights(np.zeros((10,1)) + a3, (10,1))
  s4.set_weights(np.zeros((10,1)) + a4, (10,1))

  w1 = s1.get_weights()
  w2 = s2.get_weights()
  w3 = s3.get_weights()
  w4 = s4.get_weights()


  aggregate += w1
  aggregate += w2
  aggregate += w4
  
  sec1 = s1.get_secret()
  sec2 = s2.get_secret()
  sec4 = s4.get_secret()

  aggregate += sec1
  aggregate += sec2
  aggregate += sec4

  r1 = s1.get_reveal_secret([3])
  r2 = s2.get_reveal_secret([3])
  r4 = s4.get_reveal_secret([3])

  aggregate += r1
  aggregate += r2
  aggregate += r4

  print("FINAL WEIGHTS 4:", aggregate)

