import os
import glob
import shutil
import zipfile
import subprocess
import requests
import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

BASE_DIR = "C:/Server Lokal Testing"
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

class FetchRequest(BaseModel):
    url: str

class DownloadRequest(BaseModel):
    url: str
    is_audio: bool = False
    selected_indices: Optional[List[int]] = None

def clear_download_folder():
    for item in os.listdir(DOWNLOAD_DIR):
        p = os.path.join(DOWNLOAD_DIR, item)
        try:
            if os.path.isfile(p) or os.path.islink(p):
                os.unlink(p)
            elif os.path.isdir(p):
                shutil.rmtree(p)
        except Exception:
            pass

@app.post("/fetch-metadata")
def fetch_metadata(req: FetchRequest):
    url = req.url.strip()

    # Spotify
    if "spotify.com" in url:
        try:
            clear_download_folder()
            cmd = ["spotdl", "save", url, "--save-file", f"{DOWNLOAD_DIR}/temp.spotdl"]
            subprocess.run(cmd, capture_output=True, text=True)
            spotdl_file = f"{DOWNLOAD_DIR}/temp.spotdl"
            if not os.path.exists(spotdl_file):
                return {"is_collection": False, "items": [{"id": 1, "title": "Spotify Track"}]}
            with open(spotdl_file, "r", encoding="utf-8") as f:
                tracks = json.load(f)
            items = [{"id": i + 1, "title": f"{t.get('artist', '')} - {t.get('name', '')}"} for i, t in enumerate(tracks)]
            return {"is_collection": len(items) > 1, "items": items}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Gagal membaca Spotify: {str(e)}")

    # YouTube / Mix
    import yt_dlp
    ydl_opts = {
        'extract_flat': 'in_playlist',
        'skip_download': True,
        'playlistend': 100,  # Ambil hingga 100 lagu agar HP bisa nampilin lengkap
        'quiet': True
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if 'entries' in info and info['entries']:
                items = [{"id": i + 1, "title": entry.get('title', f'Track {i + 1}')} for i, entry in enumerate(info['entries']) if entry]
                return {"is_collection": True, "items": items}
            return {"is_collection": False, "items": [{"id": 1, "title": info.get('title', 'Single Media')}]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal membaca metadata: {str(e)}")

@app.post("/download")
def download_stream(req: DownloadRequest):
    clear_download_folder()
    url = req.url.strip()

    def stream_generator():
        yield "STATUS:Menyiapkan antrian unduhan...\n"

        # TIKTOK
        if "tiktok.com" in url:
            try:
                res = requests.get(f"https://www.tikwm.com/api/?url={url}", headers={"User-Agent": "Mozilla/5.0"}).json()
                data = res.get("data", {})
                title = "".join([c for c in data.get("title", "tiktok") if c.isalnum() or c in " _-"])[:30]
                m_url = data.get("music") if req.is_audio else (data.get("hdplay") or data.get("play"))
                ext = "mp3" if req.is_audio else "mp4"
                out_file = os.path.join(DOWNLOAD_DIR, f"{title}.{ext}")

                yield f"STATUS:[TikTok] Mengunduh berkas {ext.upper()}...\n"
                with requests.get(m_url, stream=True) as stream:
                    stream.raise_for_status()
                    with open(out_file, "wb") as f:
                        for chunk in stream.iter_content(chunk_size=8192):
                            f.write(chunk)
                yield f"DONE:{os.path.basename(out_file)}\n"
                return
            except Exception as e:
                yield f"ERROR:TikTok Error: {str(e)}\n"
                return

        # YOUTUBE & PLATFORM LAINNYA
        out_tmpl = f"{DOWNLOAD_DIR}/%(title).40s.%(ext)s"
        cmd = ["yt-dlp", "--newline", "--no-colors"]

        if req.is_audio:
            cmd += ["-x", "--audio-format", "mp3", "--audio-quality", "192K"]
        else:
            cmd += ["-f", "best[ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best", "--merge-output-format", "mp4"]

        # Server HANYA mendownload indeks yang dipilih dari Android
        if req.selected_indices:
            cmd += ["--playlist-items", ",".join(str(i) for i in req.selected_indices)]

        cmd += ["-o", out_tmpl, url]

        yield "STATUS:[yt-dlp] Menghubungkan ke media...\n"
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)

        for line in proc.stdout:
            clean = line.strip()
            if "Downloading item" in clean or "[download]" in clean or "[ExtractAudio]" in clean or "[Merger]" in clean:
                yield f"STATUS:{clean}\n"

        proc.wait()

        pat = f"{DOWNLOAD_DIR}/*.mp3" if req.is_audio else f"{DOWNLOAD_DIR}/*.mp4"
        files = glob.glob(pat)
        if not files:
            yield "ERROR:Media tidak ditemukan setelah diproses\n"
            return

        if len(files) > 1:
            yield "STATUS:Mengompres ke dalam file ZIP...\n"
            zname = os.path.join(DOWNLOAD_DIR, "Selected_Collection.zip")
            with zipfile.ZipFile(zname, 'w', zipfile.ZIP_DEFLATED) as zf:
                for f in files:
                    zf.write(f, os.path.basename(f))
            yield f"DONE:Selected_Collection.zip\n"
        else:
            yield f"DONE:{os.path.basename(files[0])}\n"

    return StreamingResponse(stream_generator(), media_type="text/plain")

@app.get("/get-file/{filename}")
def get_file(filename: str):
    fpath = os.path.join(DOWNLOAD_DIR, filename)
    if not os.path.exists(fpath):
        raise HTTPException(status_code=404, detail="File tidak ditemukan")
    return FileResponse(path=fpath, filename=filename, media_type='application/octet-stream')

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)