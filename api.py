from typing import Any, Dict, List
from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
import requests, json, uvicorn
from bs4 import BeautifulSoup
from requests.exceptions import RequestException

class StreamingURLExtractor:
    def __init__(self, video_url: str):
        self.video_url = video_url
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0"
        })

    # ------------------------------------------------------------
    # Network
    # ------------------------------------------------------------
    def fetch_page(self) -> str:
        r = self.session.get(self.video_url, timeout=20)
        r.raise_for_status()
        return r.text

    # ------------------------------------------------------------
    # Media definitions
    # ------------------------------------------------------------
    def extract_streaming_urls(self) -> List[Dict[str, Any]]:
        html = self.fetch_page()

        key = '"mediaDefinitions":'
        idx = html.find(key)
        if idx == -1:
            return []

        idx += len(key)
        depth = 0
        start = end = None

        for i in range(idx, len(html)):
            if html[i] == "[":
                depth += 1
                if start is None:
                    start = i
            elif html[i] == "]":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break

        if start is None or end is None:
            return []

        try:
            raw_defs = json.loads(html[start:end])
        except Exception:
            return []

        return self._normalize_media_definitions(raw_defs)

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------
    def resolve_stream_url(self, url: str) -> str:
        try:
            r = self.session.head(url, allow_redirects=True, timeout=10)
            return r.url
        except Exception:
            return url

    def _normalize_media_definitions(self, defs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []

        for d in defs:
            url = d.get("videoUrl") or d.get("url")
            if not url:
                continue

            height = d.get("quality")

            fmt = d.get("format") or d.get("videoFormat") or ""
            resolved_url = self.resolve_stream_url(url)

            out.append({
                "quality": height,
                "format": fmt.lower(),
                "url": resolved_url,
                "Developer": "Silent Ghost",
            })

        return out

    # ------------------------------------------------------------
    # Save output
    # ------------------------------------------------------------
    def save(self) -> Dict[str, Any]:
        data = {
            "video_url": self.video_url,
            "streaming_urls": self.extract_streaming_urls()
        }

        return data

app = FastAPI(
    title="Streaming URL Extractor API",
    version="1.0.1",
)

@app.get("/")
def extract(url: str = Query(..., description="Target video page URL")):
    extractor = StreamingURLExtractor(url)
    return extractor.save()

if __name__ == "__main__":
    app.run()
