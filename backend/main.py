"""GRABLYX API: public metadata and permitted source formats, no DRM or login bypass."""
import os
import ipaddress
import socket
import re
import hmac
import hashlib
import base64
import json
import time
import secrets
import httpx
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp

app = FastAPI(title="GRABLYX API")
SIGNING_KEY = os.getenv("DOWNLOAD_SIGNING_KEY", "").encode() or secrets.token_bytes(32)
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
            try:
                info = ydl.extract_info(url, download=False)
            except yt_dlp.utils.DownloadError as primary_error:
                parsed = urlparse(url)
                match = re.fullmatch(r"/reel/(\\d+)/?", parsed.path)
                if parsed.hostname in ("facebook.com", "www.facebook.com", "m.facebook.com") and match:
                    reel_id = match.group(1)
                    alternatives = (
                        "https://www.facebook.com/watch/?v=" + reel_id,
                        "https://m.facebook.com/watch/?v=" + reel_id,
                        "https://www.facebook.com/video.php?v=" + reel_id,
                    )
                    info = None
                    for alternate in alternatives:
                        try:
                            info = ydl.extract_info(alternate, download=False)
                            if info:
                                break
                        except yt_dlp.utils.DownloadError:
                            continue
                    if not info:
                        raise primary_error
                else:
                    raise
        if not info:
            raise HTTPException(422, "No hay contenido multimedia accesible.")
        # Some extractors return one playable URL rather than a formats array.
        candidates = info.get("formats") or ([info] if info.get("url") else [])
        formats = []
        seen = set()
        for f in candidates:
            direct = f.get("url")
            if not direct or f.get("has_drm") or f.get("protocol", "https") not in ("http", "https"):
                continue
            if urlparse(direct).scheme not in ("http", "https"):
                continue
            if direct in seen:
                continue
            seen.add(direct)
            payload = json.dumps({"u": direct, "e": int(time.time()) + 900, "x": f.get("ext") or "mp4"}, separators=(",", ":")).encode()
            sig = hmac.new(SIGNING_KEY, payload, hashlib.sha256).digest()
            token = base64.urlsafe_b64encode(payload + sig).decode().rstrip("=")
            formats.append({"download": "/download?token=" + token, "id": f.get("format_id"), "ext": f.get("ext"),
                            "height": f.get("height"),
                            "audio": f.get("acodec") != "none" and (f.get("acodec") is not None or f.get("vcodec") == "none"),
                            "video": f.get("vcodec") != "none" and (f.get("vcodec") is not None or f.get("acodec") == "none" or f.get("ext") in ("mp4", "webm", "mov")),
                            "url": direct})
        return {"title": info.get("title"), "thumbnail": info.get("thumbnail"),
                "duration": info.get("duration"), "formats": formats[:80]}
    except HTTPException:
        raise
    except yt_dlp.utils.DownloadError as exc:
        reason = str(exc).lower()
        if any(term in reason for term in ("login", "sign in", "cookies", "private")):
            raise HTTPException(422, "El contenido requiere autenticación o no es público.")
        if "cannot parse data" in reason:
            raise HTTPException(422, "El extractor no pudo interpretar la respuesta de Facebook. Puede ser una restricción o un cambio de formato.")
        if "unsupported url" in reason or "no video" in reason:
            raise HTTPException(422, "Enlace no reconocido. Prueba la URL directa de una publicación pública.")
        if "429" in reason or "rate" in reason or "blocked" in reason:
            raise HTTPException(503, "La plataforma limita temporalmente el acceso desde este servidor.")
        raise HTTPException(422, "La plataforma no entregó contenido accesible. Prueba la URL directa del Reel.")
    except Exception:
        raise HTTPException(422, "Error al analizar este enlace público.")

@app.get("/download")
async def download(token: str):
    try:
        raw = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))
        payload, signature = raw[:-32], raw[-32:]
        if not hmac.compare_digest(hmac.new(SIGNING_KEY, payload, hashlib.sha256).digest(), signature):
            raise ValueError("bad signature")
        data = json.loads(payload)
        if data["e"] < time.time():
            raise HTTPException(410, "El enlace caducó. Analiza la publicación de nuevo.")
        source = data["u"]
        parsed = urlparse(source)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None, 443):
            raise ValueError("invalid source")
        # The signed token must only point to recognized public media CDNs.
        cdn_hosts = ("fbcdn.net", "cdninstagram.com", "googlevideo.com",
                     "tiktokcdn.com", "tiktokv.com", "twimg.com", "redd.it",
                     "redditmedia.com", "pinimg.com")
        host = parsed.hostname.lower().rstrip(".")
        if not any(host == d or host.endswith("." + d) for d in cdn_hosts):
            raise ValueError("unrecognized media host")
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
            raise ValueError("nonpublic source")
    except HTTPException:
        raise
    except (ValueError, KeyError, TypeError, OverflowError, json.JSONDecodeError, socket.gaierror):
        raise HTTPException(400, "Enlace de descarga inválido.")
    client = httpx.AsyncClient(follow_redirects=False, timeout=httpx.Timeout(25, connect=8), trust_env=False)
    try:
        request = client.build_request("GET", source)
        response = await client.send(request, stream=True)
        if response.status_code != 200:
            await response.aclose()
            await client.aclose()
            raise HTTPException(502, "El archivo ya no está disponible. Vuelve a analizar el enlace.")
        content_type = response.headers.get("content-type", "").lower()
        if content_type.startswith(("text/html", "application/json", "text/xml")):
            await response.aclose()
            await client.aclose()
            raise HTTPException(502, "El origen no entregó un archivo multimedia.")
        size = response.headers.get("content-length")
        if size and int(size) > 250_000_000:
            await response.aclose()
            await client.aclose()
            raise HTTPException(413, "Este archivo supera el límite temporal de descarga.")
    except HTTPException:
        raise
    except Exception:
        await client.aclose()
        raise HTTPException(502, "No se pudo iniciar la descarga.")
    async def chunks():
        total = 0
        try:
            async for chunk in response.aiter_bytes(65536):
                total += len(chunk)
                if total > 250_000_000:
                    break
                yield chunk
        finally:
            await response.aclose()
            await client.aclose()
    ext = re.sub(r"[^a-z0-9]", "", str(data.get("x", "mp4")).lower())[:6] or "mp4"
    return StreamingResponse(chunks(), media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="grablyx.{ext}"',
                 "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})
