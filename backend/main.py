"""GRABLYX API: public metadata and permitted source formats, no DRM or login bypass."""
import os
import ipaddress
import socket
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp

app = FastAPI(title="GRABLYX API")
allowed = [x.strip() for x in os.getenv("ALLOWED_ORIGINS", "https://clickgraphics.github.io").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=allowed, allow_methods=["POST","GET"], allow_headers=["Content-Type"])

class Link(BaseModel):
    url: str

def validate(raw: str):
    parsed = urlparse(raw)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise HTTPException(400, "Se requiere una URL HTTPS pública.")
    host = parsed.hostname.lower()
    supported = (
        "youtube.com", "youtu.be", "facebook.com", "fb.watch",
        "instagram.com", "tiktok.com", "x.com", "twitter.com",
        "pinterest.com", "pin.it", "reddit.com", "redd.it"
    )
    if not any(host == domain or host.endswith("." + domain) for domain in supported):
        raise HTTPException(400, "Plataforma no admitida por el servidor.")
    try:
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        if any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
            raise HTTPException(400, "Destino no público.")
    except socket.gaierror:
        raise HTTPException(400, "Dominio no encontrado.")
    return raw

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/analyze")
def analyze(link: Link):
    url = validate(link.url)
    opts = {"skip_download": True, "noplaylist": True, "extract_flat": False,
            "socket_timeout": 8, "retries": 0, "playlistend": 1,
            "ignoreerrors": False, "quiet": True, "no_warnings": True}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        if not info:
            raise HTTPException(422, "No hay contenido multimedia accesible.")
        formats = []
        for f in info.get("formats", []):
            direct = f.get("url")
            if not direct or f.get("has_drm") or f.get("protocol") not in ("http", "https"):
                continue
            formats.append({"id": f.get("format_id"), "ext": f.get("ext"),
                            "height": f.get("height"), "audio": f.get("acodec") != "none",
                            "video": f.get("vcodec") != "none", "url": direct})
        return {"title": info.get("title"), "thumbnail": info.get("thumbnail"),
                "duration": info.get("duration"), "formats": formats[:80]}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(422, "No se pudo analizar este enlace público.")
