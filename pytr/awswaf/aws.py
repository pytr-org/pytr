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

import json
import random
import re

from curl_cffi import requests

from .fingerprint import get_fp
from .verify import CHALLENGE_SOLVERS


def parse_challenge_js(js_text: str) -> dict:
    """Extract WAF constants from challenge.js at runtime.

    Matches on structural patterns and string literal values, not on obfuscated
    property names (which change on every JS rebuild).

    Returns a dict with:
        challenge_types: {hash: endpoint_name} e.g. {"h72f9...": "verify", "ha9fa...": "mp_verify"}
        mp_field_names: (solution_field, metadata_field) for multipart submissions
        bandwidth_sizes: {difficulty: size_bytes}
    """
    # --- Challenge type hash → endpoint name ---
    # The JS assigns hashes to 'verify' or 'mp_verify', but the hashes are split
    # across obfuscated string concatenations that we can't resolve without a JS
    # runtime. Instead, we extract all endpoint names used and match them to hashes
    # at solve time using the hash prefix visible in the JS.
    # Pattern: 'h<hex_prefix>'+...']='verify' or 'mp_verify'
    challenge_types = {}
    for m in re.finditer(r"'(h[0-9a-f]{8,})'[+].*?=\s*'((?:mp_)?verify)'", js_text):
        # Store by prefix — we'll match against the full hash from /inputs later
        challenge_types[m.group(1)] = m.group(2)

    # --- Multipart form field names ---
    # Near the string 'verify' there are also 'solution_data' and 'solution_metadata'
    # Match: ...'verify'...'solution_data'...'solution_metadata'... (within ~200 chars)
    mp_solution_field = "solution_data"
    mp_metadata_field = "solution_metadata"
    field_match = re.search(
        r"'verify'\s*,\s*'\w+'\s*:\s*'(solution_\w+)'\s*,\s*'\w+'\s*:\s*'(solution_\w+)'",
        js_text,
    )
    if field_match:
        mp_solution_field = field_match.group(1)
        mp_metadata_field = field_match.group(2)

    # --- Buffer sizes for NetworkBandwidth ---
    # switch(difficulty) with hex constants: case 0x1:return 0x400;...
    bandwidth_sizes = {}
    size_match = re.search(
        r"case\s+0x1:return\s+(0x[0-9a-f]+);"
        r"case\s+0x2:return[^;]*\((0x[0-9a-f]+),(0x[0-9a-f]+)\);"
        r"case\s+0x3:return[^;]*\((0x[0-9a-f]+),(0x[0-9a-f]+)\);"
        r"case\s+0x4:return[^;]*\((0x[0-9a-f]+),(0x[0-9a-f]+)\);"
        r"case\s+0x5:return[^;]*\((0x[0-9a-f]+),(0x[0-9a-f]+)\)",
        js_text,
    )
    if size_match:
        bandwidth_sizes = {
            1: int(size_match.group(1), 16),
            2: int(size_match.group(2), 16) * int(size_match.group(3), 16),
            3: int(size_match.group(4), 16) * int(size_match.group(5), 16),
            4: int(size_match.group(6), 16) * int(size_match.group(7), 16),
            5: int(size_match.group(8), 16) * int(size_match.group(9), 16),
        }

    return {
        "challenge_types": challenge_types,
        "mp_field_names": (mp_solution_field, mp_metadata_field),
        "bandwidth_sizes": bandwidth_sizes,
    }


class AwsWaf:
    def __init__(
        self,
        endpoint: str,
        domain: str,
        challenge_js_text: str = "",
        user_agent: str = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
        ),
    ):
        self.session: requests.Session = requests.Session(impersonate="chrome")
        self.session.headers.update(
            {
                "connection": "keep-alive",
                "sec-ch-ua-platform": '"Windows"',
                "user-agent": user_agent,
                "sec-ch-ua": '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
                "sec-ch-ua-mobile": "?0",
                "accept": "*/*",
                "sec-fetch-site": "cross-site",
                "sec-fetch-mode": "cors",
                "sec-fetch-dest": "empty",
                "accept-encoding": "gzip, deflate, br, zstd",
                "accept-language": "en-US,en;q=0.9",
            }
        )
        self.user_agent = user_agent
        self.domain = domain
        self.endpoint = endpoint

        # Parse constants from challenge.js
        self._js_config = parse_challenge_js(challenge_js_text)

    def get_inputs(self):
        return self.session.get(f"https://{self.endpoint}/inputs?client=browser").json()

    def build_payload(self, inputs: dict):
        challenge_type = inputs["challenge_type"]
        solver = CHALLENGE_SOLVERS.get(challenge_type)
        if solver is None:
            # Fall back: check if it maps to a known endpoint in challenge.js config
            if self._get_endpoint(challenge_type) == "mp_verify":
                from .verify import network_bandwidth

                solver = network_bandwidth
            else:
                raise ValueError(f"Unknown challenge type: {challenge_type}")

        checksum, fp = get_fp(self.user_agent)
        bandwidth_sizes = self._js_config.get("bandwidth_sizes", {})
        solution = solver(inputs["challenge"]["input"], checksum, inputs["difficulty"], bandwidth_sizes=bandwidth_sizes)
        return {
            "challenge": inputs["challenge"],
            "checksum": checksum,
            "solution": solution,
            "signals": [{"name": "Zoey", "value": {"Present": fp}}],
            "existing_token": None,
            "client": "Browser",
            "domain": self.domain,
            "metrics": [
                {"name": "2", "value": random.uniform(0, 1), "unit": "2"},
                {"name": "100", "value": 0, "unit": "2"},
                {"name": "101", "value": 0, "unit": "2"},
                {"name": "102", "value": 0, "unit": "2"},
                {"name": "103", "value": 8, "unit": "2"},
                {"name": "104", "value": 0, "unit": "2"},
                {"name": "105", "value": 0, "unit": "2"},
                {"name": "106", "value": 0, "unit": "2"},
                {"name": "107", "value": 0, "unit": "2"},
                {"name": "108", "value": 1, "unit": "2"},
                {"name": "undefined", "value": 0, "unit": "2"},
                {"name": "110", "value": 0, "unit": "2"},
                {"name": "111", "value": 2, "unit": "2"},
                {"name": "112", "value": 0, "unit": "2"},
                {"name": "undefined", "value": 0, "unit": "2"},
                {"name": "3", "value": 4, "unit": "2"},
                {"name": "7", "value": 0, "unit": "4"},
                {"name": "1", "value": random.uniform(10, 20), "unit": "2"},
                {"name": "4", "value": 36.5, "unit": "2"},
                {"name": "5", "value": random.uniform(0, 1), "unit": "2"},
                {"name": "6", "value": random.uniform(50, 60), "unit": "2"},
                {"name": "0", "value": random.uniform(130, 140), "unit": "2"},
                {"name": "8", "value": 1, "unit": "4"},
            ],
        }

    def _get_endpoint(self, challenge_type: str) -> str:
        """Resolve challenge type hash to endpoint name using prefix matching."""
        ct = self._js_config["challenge_types"]
        # Try exact match first, then prefix match
        if challenge_type in ct:
            return ct[challenge_type]
        for prefix, endpoint in ct.items():
            if challenge_type.startswith(prefix):
                return endpoint
        return "verify"

    def verify(self, payload, challenge_type):
        self.session.headers.update(
            {
                "connection": "keep-alive",
                "sec-ch-ua-platform": '"Windows"',
                "user-agent": self.user_agent,
                "sec-ch-ua-mobile": "?0",
                "accept": "*/*",
                "sec-fetch-site": "cross-site",
                "sec-fetch-mode": "cors",
                "sec-fetch-dest": "empty",
                "accept-encoding": "gzip, deflate, br, zstd",
                "accept-language": "en-US,en;q=0.9",
            }
        )

        endpoint_name = self._get_endpoint(challenge_type)
        if endpoint_name == "mp_verify":
            import requests as std_requests  # type: ignore[import-untyped]

            solution_field, metadata_field = self._js_config["mp_field_names"]
            solution = payload.pop("solution")
            payload["solution"] = None
            res = std_requests.post(
                f"https://{self.endpoint}/{endpoint_name}",
                files={
                    solution_field: (None, solution),
                    metadata_field: (None, json.dumps(payload)),
                },
                headers={"user-agent": self.user_agent},
            ).json()
        else:
            self.session.headers["content-type"] = "text/plain;charset=UTF-8"
            res = self.session.post(f"https://{self.endpoint}/verify", json=payload).json()

        return res["token"]

    def __call__(self):
        inputs = self.get_inputs()
        payload = self.build_payload(inputs)
        return self.verify(payload, inputs["challenge_type"])
