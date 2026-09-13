# Downloader Everything — Backend

Backend server untuk aplikasi Android **Downloader Everything**. Server ini menerima permintaan dari aplikasi, memproses pengunduhan media dari berbagai platform, lalu mengirim hasilnya kembali ke perangkat pengguna.

Backend server for the **Downloader Everything** Android app. It receives requests from the app, processes media downloads from various platforms, and sends the result back to the user's device.

---

## Fitur / Features

- Unduh video (MP4) dan audio (MP3) dari YouTube, TikTok, dan platform lain yang didukung `yt-dlp`
  Download video (MP4) and audio (MP3) from YouTube, TikTok, and other platforms supported by `yt-dlp`
- Unduh audio dari Spotify menggunakan `SpotDL`
  Download audio from Spotify using `SpotDL`
- Unduh foto/galeri dari Pinterest dan situs lain menggunakan `gallery-dl`
  Download photos/galleries from Pinterest and other sites using `gallery-dl`
- Dukungan playlist/album dengan pemilihan track tertentu
  Playlist/album support with selective track picking
- Proses berjalan di background (job-based), status dicek lewat polling — lebih stabil dibanding streaming response lewat tunnel gratis
  Background job processing with status polling — more reliable than streaming responses over free tunnels

---

## Tech Stack

- **FastAPI** — REST API framework
- **yt-dlp** — video/audio extractor untuk YouTube, TikTok, dan ratusan situs lain
- **SpotDL** — Spotify track downloader
- **gallery-dl** — image/gallery downloader
- **Cloudflare Tunnel** — expose server lokal ke domain publik tanpa perlu port forwarding

---

## Cara Kerja / How It Works

1. Aplikasi mengirim `POST /download` berisi URL dan tipe konten (`video` / `audio` / `photo`)
   The app sends `POST /download` with a URL and content type (`video` / `audio` / `photo`)
2. Server membuat job di background dan langsung mengembalikan `job_id`
   The server starts a background job and immediately returns a `job_id`
3. Aplikasi melakukan polling ke `GET /status/{job_id}` secara berkala untuk memantau progres
   The app polls `GET /status/{job_id}` periodically to track progress
4. Setelah selesai, file diambil lewat `GET /get-file/{file_name}`
   Once done, the file is retrieved via `GET /get-file/{file_name}`

---

## Endpoint

| Method | Path | Deskripsi / Description |
|---|---|---|
| POST | `/download` | Memulai proses unduh, mengembalikan `job_id` — Starts a download job, returns `job_id` |
| GET | `/status/{job_id}` | Mengecek status job — Checks job status |
| GET | `/get-file/{file_name}` | Mengunduh file hasil — Downloads the resulting file |
| POST | `/fetch-metadata` | Mengambil daftar item dari playlist/album — Fetches item list from a playlist/album |

---

## Menjalankan Server / Running the Server

```bash
pip install fastapi uvicorn yt-dlp spotdl gallery-dl --break-system-packages
uvicorn server:app --host 0.0.0.0 --port 8001
```

Server ini dirancang untuk dijalankan di belakang reverse proxy / tunnel (misalnya Cloudflare Tunnel) agar bisa diakses dari luar jaringan lokal.
This server is designed to run behind a reverse proxy / tunnel (e.g. Cloudflare Tunnel) so it can be accessed from outside the local network.

---

## Catatan / Notes

Beberapa konten mungkin gagal diunduh karena keterbatasan dari platform sumber, bukan bug pada server ini — misalnya konten yang membutuhkan login, dibatasi wilayah, atau memang tidak menyediakan file media terpisah (contoh: foto dengan musik latar di beberapa platform sosial).
Some content may fail to download due to limitations from the source platform, not a bug in this server — for example, content that requires login, is region-locked, or simply does not provide a separate downloadable media file (e.g. photos with background music on certain social platforms).

Proyek ini dibuat untuk keperluan pribadi/pembelajaran. Gunakan sesuai dengan ketentuan layanan masing-masing platform.
This project was built for personal/learning purposes. Use it in accordance with each platform's terms of service.
