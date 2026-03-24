# MIT License
#
# Copyright (c) 2025
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Vendored from https://github.com/xKiian/awswaf
#

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

key = bytes.fromhex("6f71a512b1e035eaab53d8be73120d3fb68a0ca346b9560aab3e5cdf753d5e98")
aesgcm = AESGCM(key)


def encrypt(plaintext: bytes) -> str:
    iv = os.urandom(12)
    cipher_bytes = aesgcm.encrypt(iv, plaintext, None)
    tag = cipher_bytes[-16:]
    ciphertext = cipher_bytes[:-16]
    iv_b64 = base64.b64encode(iv).decode("utf-8")
    return f"{iv_b64}::{tag.hex()}::{ciphertext.hex()}"


def decrypt(encrypted: str) -> bytes:
    iv_b64, tag_hex, ct_hex = encrypted.split("::")
    iv = base64.b64decode(iv_b64)
    tag = bytes.fromhex(tag_hex)
    ciphertext = bytes.fromhex(ct_hex)
    return aesgcm.decrypt(iv, ciphertext + tag, None)
