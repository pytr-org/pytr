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
# Applied patch from https://github.com/xKiian/awswaf/pull/4
#

import binascii
import hashlib
import itertools
from typing import Any, Callable, Optional


def _check(digest: bytes, difficulty: int) -> bool:
    full, rem = divmod(difficulty, 8)
    if digest[:full] != b"\x00" * full:
        return False
    if rem and (digest[full] >> (8 - rem)):
        return False
    return True


def hash_pow(challenge: str, salt: str, difficulty: int) -> Optional[str]:
    prefix = (challenge + salt).encode()
    for nonce in itertools.count():
        digest = hashlib.sha256(prefix + str(nonce).encode()).digest()
        if _check(digest, difficulty):
            return str(nonce)
    return None


def scrypt_func(
    input_str: str, salt: str, n: int = 128, r: int = 8, p: int = 1, dklen: int = 16
) -> str:
    raw = hashlib.scrypt(
        password=input_str.encode(), salt=salt.encode(), n=n, r=r, p=p, dklen=dklen
    )
    return binascii.hexlify(raw).decode()


def compute_scrypt_nonce(
    challenge: str,
    salt: str,
    difficulty: int,
    n: int = 128,
    r: int = 8,
    p: int = 1,
    dklen: int = 16,
) -> Optional[str]:
    prefix = challenge + salt
    for nonce in itertools.count():
        digest = hashlib.scrypt(
            password=f"{prefix}{nonce}".encode(),
            salt=salt.encode(),
            n=n,
            r=r,
            p=p,
            dklen=dklen,
        )
        if _check(digest, difficulty):
            return str(nonce)
    return None


def network_bandwidth(challenge: str, salt: str, difficulty: int) -> str:
    """NetworkBandwidth challenge — returns a dummy solution accepted at low difficulty."""
    return "0"


CHALLENGE_TYPES: dict[str, Callable[..., Any]] = {
    "h72f957df656e80ba55f5d8ce2e8c7ccb59687dba3bfb273d54b08a261b2f3002": compute_scrypt_nonce,
    "h7b0c470f0cfe3a80a9e26526ad185f484f6817d0832712a4a37a908786a6a67f": hash_pow,
    "ha9faaffd31b4d5ede2a2e19d2d7fd525f66fee61911511960dcbb52d3c48ce25": network_bandwidth,
}
