"""Shared utilities for infra source modules."""


def _fetch(url, timeout=8, headers=None):
    """Fetch URL and return response text."""
    hdrs = {"User-Agent": "Mozilla/5.0"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, headers=hdrs)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _fetch_json(url, timeout=8, headers=None):
    """Fetch URL and return parsed JSON."""
    text = _fetch(url, timeout, headers)
    return json.loads(text)
