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
import time
from typing import Any, Callable, Optional

# Bounds for the two proof-of-work solvers below.
#
# Both used to loop over `itertools.count()` with no exit other than success,
# while `difficulty` arrives from the WAF's own `/inputs` response — so the
# server on the other end decided how long this process would spin. Two ways
# that ends badly: a difficulty above 256 can never be satisfied at all
# (`_check` compares a 32-byte digest against a longer all-zero prefix, which
# is false for every possible digest), and values below that are already
# computationally out of reach while still looking like a legitimate
# challenge. Either way a login someone is waiting on hangs forever.
#
# Giving up returns `None`, which `build_payload` turns into a clean error.
# A WAF token that takes longer than the deadline is worthless anyway: the
# caller is a synchronous login request.
_MAX_SOLVABLE_DIFFICULTY = 256
_POW_DEADLINE_SECONDS = 30.0
# The deadline is only consulted every N nonces — a `time.monotonic()` call per
# sha256 would cost more than the hash it is guarding. scrypt is expensive
# enough per iteration to check every time.
_POW_TIME_CHECK_INTERVAL = 4096


def _check(digest: bytes, difficulty: int) -> bool:
    full, rem = divmod(difficulty, 8)
    if digest[:full] != b"\x00" * full:
        return False
    if rem and (digest[full] >> (8 - rem)):
        return False
    return True


def hash_pow(challenge: str, salt: str, difficulty: int, **kwargs) -> Optional[str]:
    if difficulty > _MAX_SOLVABLE_DIFFICULTY:
        return None
    prefix = (challenge + salt).encode()
    deadline = time.monotonic() + _POW_DEADLINE_SECONDS
    for nonce in itertools.count():
        digest = hashlib.sha256(prefix + str(nonce).encode()).digest()
        if _check(digest, difficulty):
            return str(nonce)
        if nonce % _POW_TIME_CHECK_INTERVAL == 0 and time.monotonic() > deadline:
            return None
    return None


def scrypt_func(input_str: str, salt: str, n: int = 128, r: int = 8, p: int = 1, dklen: int = 16) -> str:
    raw = hashlib.scrypt(password=input_str.encode(), salt=salt.encode(), n=n, r=r, p=p, dklen=dklen)
    return binascii.hexlify(raw).decode()


def compute_scrypt_nonce(
    challenge: str,
    salt: str,
    difficulty: int,
    n: int = 128,
    r: int = 8,
    p: int = 1,
    dklen: int = 16,
    **kwargs,
) -> Optional[str]:
    if difficulty > _MAX_SOLVABLE_DIFFICULTY:
        return None
    prefix = challenge + salt
    deadline = time.monotonic() + _POW_DEADLINE_SECONDS
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
        if time.monotonic() > deadline:
            return None
    return None


_DEFAULT_BANDWIDTH_SIZES = {1: 0x400, 2: 0xA * 0x400, 3: 0x64 * 0x400, 4: 0x100000, 5: 0xA * 0x100000}

# The largest entry in the table above. `bandwidth_sizes` can also arrive from
# `parse_challenge_js`, i.e. from numbers scraped out of a page with a regular
# expression, and the buffer is allocated in one go. Without a ceiling a single
# rewritten constant turns into an out-of-memory kill of the whole process —
# which, in this application, is the process holding the user's session.
_MAX_BANDWIDTH_BYTES = 0xA * 0x100000


def network_bandwidth(challenge: str, salt: str, difficulty: int, **kwargs) -> str:
    """NetworkBandwidth challenge — returns base64-encoded zero buffer sized by difficulty."""
    import base64

    sizes = kwargs.get("bandwidth_sizes") or _DEFAULT_BANDWIDTH_SIZES
    size = sizes.get(difficulty, 0x400)
    try:
        size = int(size)
    except (TypeError, ValueError):
        size = 0x400
    size = min(max(size, 0), _MAX_BANDWIDTH_BYTES)
    return base64.b64encode(b"\x00" * size).decode()


# Known challenge type hashes → solver functions.
# The challenge.js is also parsed at runtime to discover endpoint names and new types.
CHALLENGE_SOLVERS: dict[str, Callable[..., Any]] = {
    "h72f957df656e80ba55f5d8ce2e8c7ccb59687dba3bfb273d54b08a261b2f3002": compute_scrypt_nonce,
    "h7b0c470f0cfe3a80a9e26526ad185f484f6817d0832712a4a37a908786a6a67f": hash_pow,
    "ha9faaffd31b4d5ede2a2e19d2d7fd525f66fee61911511960dcbb52d3c48ce25": network_bandwidth,
}
