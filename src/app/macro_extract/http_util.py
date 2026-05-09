import httpx

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; WroclawMacroFinder/0.1; +https://github.com/)"
    ),
}


def fetch_text(url: str, timeout: float = 30.0) -> str:
    with httpx.Client(headers=DEFAULT_HEADERS, follow_redirects=True) as client:
        r = client.get(url, timeout=timeout)
        r.raise_for_status()
        return r.text


def fetch_bytes(url: str, timeout: float = 30.0) -> bytes:
    with httpx.Client(headers=DEFAULT_HEADERS, follow_redirects=True) as client:
        r = client.get(url, timeout=timeout)
        r.raise_for_status()
        return r.content
