#! /usr/bin/env python3
from Crypto.Cipher import AES
import base64, os

def gen_key():
  return os.urandom(32)

def encrypt(msg, secret_key, padding_character="^"):
  private_msg = base64.b64encode(msg).decode("utf-8")
  cipher = AES.new(secret_key)
  padded_private_msg = private_msg + (padding_character * ((16-len(private_msg)) % 16))
  return cipher.encrypt(padded_private_msg)

def decrypt(encrypted_msg, secret_key, padding_character="^"):
  cipher = AES.new(secret_key)
  decrypted_msg = cipher.decrypt(encrypted_msg)
  unpadded_private_msg = decrypted_msg.decode("utf8").rstrip(padding_character)
  return base64.b64decode(unpadded_private_msg)

