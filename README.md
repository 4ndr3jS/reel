# REEL — Keep the good stuff

A complete YouTube / TikTok download desk with MP4 and MP3 output. The frontend uses React and Vinext; a loopback-only Python engine runs yt-dlp and FFmpeg on the visitor's computer.

GitHub repository: https://github.com/4ndr3jS/reel

GitHub Pages URL (after a successful Pages deployment): https://4ndr3js.github.io/reel/

Original private Sites deployment: https://reel-download-studio-9nov.ampledulse1.chatgpt.site

## Use the site

1. Install Python 3.11+, Node.js 22.13+, and FFmpeg (including ffprobe), and add them to PATH.
2. On Windows, double-click start-reel.cmd. It installs the pinned Python dependencies in engine/.deps on first use, then starts the engine.
3. Open the Pages site and allow access to the local network if your browser asks. The header should say Engine online. Keep the engine running.
4. Paste a YouTube video, Shorts, or TikTok video/share link. Pick MP4 or MP3 and quality, find the video, then download it. Click Save file when complete.

Batch links supports up to five links at a time. Two downloads run concurrently. MP3 offers a dual-mono option that combines the original left and right audio, then sends the identical mix to both ears. Higher bitrate or resolution does not improve the source upload.

The GitHub repository is private. The GitHub Pages website is public; hosting Pages from a private repository requires GitHub Pro or another eligible paid plan. The original Sites deployment remains private to its owner. An engine is required on each visitor's computer. This is not a remote conversion service; mobile devices without a local Python/FFmpeg engine can view the responsive interface but cannot download through it.

## GitHub Pages deployment

The repository includes .github/workflows/pages.yml. Pushes to main run a static Vite build of the same React interface, then publish dist-pages using GitHub Actions. No cloud worker or Python process is deployed to Pages. The source includes the original Vinext build as a separate option.

Enable Pages under Settings > Pages > Build and deployment > GitHub Actions. The repository must be on an eligible plan for private-repository Pages. If GitHub rejects Pages activation, the repository can stay private and the build artifact remains available, but the site will not deploy until the account is eligible.

- npm run build:pages builds the static site and refreshed engine ZIP.
- npm run preview:pages previews it at http://127.0.0.1:4173/reel/.
- PAGES_BASE_PATH defaults to /reel/ and can be changed for another repository or custom domain.
- The engine allows the exact https://4ndr3js.github.io origin. If moving to another account or domain, update engine/server.py and rebuild the engine ZIP.
- GitHub Pages cannot run yt-dlp or FFmpeg. Every visitor still needs the local engine; the page has an engine-download button.

## Local development

- npm ci
- npm run dev -- --host 127.0.0.1 --port 5173
- In another terminal, run start-reel.cmd (Windows), or install engine/requirements.txt and run python engine/server.py.
- Open http://127.0.0.1:5173
- npm run build produces the Cloudflare Worker bundle and browser assets.

The native Sites hosting manifest is .openai/hosting.json. The Sites build plugin and supplied build scripts remain intact.

## Engine behavior and boundaries

The engine listens only on 127.0.0.1:8941. CORS permits the original Sites origin, the exact GitHub Pages account origin, and the explicit local development origins. POST requests require an in-memory session token, JSON, and a validated YouTube/TikTok video URL. Host checks prevent DNS rebinding. Subprocesses use argument arrays without shell interpolation. No browser cookies or credentials are read. Generated files use random identifiers and are streamed with range support.

Limits: single public videos up to three hours, 1 GB per file, two active conversions and eight queued/active jobs. The cache stops accepting new work at 4 GB (in-flight jobs may add up to their per-file limits). Restarting the engine clears its previous temporary files; save wanted files first. Browser history is local to each browser. A previous session's history can remain visible even when its temporary files are no longer available.

Private, paid, DRM-protected and live content is excluded. Platform restrictions, regional availability, deleted videos and anti-automation changes can cause individual downloads to fail. No watermark removal is promised. The selected MP4 resolution is a ceiling: the best available format at or below it is used.

The browser fetches Google Fonts and video thumbnails from their original hosts; the app has no analytics or advertising integrations.

## Checks

- node node_modules/typescript/bin/tsc --noEmit
- python -m py_compile engine/server.py
- python engine/test_engine.py (running engine required)
- python engine/test_engine.py --live (network required; retrieves actual YouTube and TikTok media)

Integration checks cover origin rejection, missing session tokens, local/private URLs, channel/playlist URLs, invalid formats, file lookup, MP4 byte-range delivery, and decoded dual-mono channel equality. Live tests depend on third-party availability.

## Updating downloader support

The tested versions are pinned in engine/requirements.txt. YouTube and TikTok change frequently. Update yt-dlp, yt-dlp-ejs and curl-cffi together in a test environment, rerun the live checks, then update the pins.

- yt-dlp: https://github.com/yt-dlp/yt-dlp
- JavaScript runtime support: https://github.com/yt-dlp/yt-dlp/wiki/EJS
- FFmpeg: https://ffmpeg.org/

Download content you own or have permission to save.
