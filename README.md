# REEL

My YouTube and TikTok downloader. Paste a link, choose MP4 or MP3, and save the file.

**[Open REEL](https://4ndr3js.github.io/reel/)**

I wanted the site to feel simple: one place for videos and audio, with the quality settings right there. I also added a “same sound in both ears” option for tracks with uneven left and right audio.

You can download individual videos, YouTube Shorts, or add up to five links at once. Two downloads run at a time, and finished files show up on the download desk.

## Getting started

The site runs on GitHub Pages, but the downloading and conversion happen on your computer. You'll need the local engine running while you use it.

For Windows:

1. Install Python 3.11+, Node.js 22.13+, and FFmpeg. Make sure `python`, `node`, `ffmpeg`, and `ffprobe` are available in your terminal.
2. [Download the engine](https://4ndr3js.github.io/reel/reel-engine.zip) and unzip it.
3. Double-click `start-reel.cmd`. It installs the Python dependencies on the first run.
4. Open REEL. Allow local-network access if your browser asks, and look for **Engine online** in the header.
5. Paste your link, pick the format and quality, then download. Hit **Save file** when it's ready.

Keep the engine window open. Save any files you want before restarting it, because a restart clears its temporary downloads.

## A few things to know

- The engine is required on each computer. The mobile layout works, but the site alone can't download files on a phone.
- It handles public videos up to three hours long, with a 1 GB limit per file. Private videos and live streams aren't supported.
- Quality depends on the original upload. Choosing 4K or a higher MP3 bitrate won't add detail that wasn't there.
- Download history stays in your browser. The files themselves stay on your computer.
- YouTube and TikTok sometimes block requests or change how their sites work, so some links may fail.

## Running it locally

```sh
npm ci
npm run build:pages
npm run preview:pages
```

Open [localhost:4173/reel/](http://127.0.0.1:4173/reel/) and run `start-reel.cmd` in a separate window.

For frontend development, use `npm run dev -- --host 127.0.0.1 --port 5173`. The Pages workflow builds and deploys pushes to `main`.

I use React and Vite for the Pages frontend, [yt-dlp](https://github.com/yt-dlp/yt-dlp) to retrieve media, and [FFmpeg](https://ffmpeg.org/) for conversion.
