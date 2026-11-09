"use client";
import { useEffect, useRef, useState } from "react";
import { ArrowUpRight, ArrowDown, ArrowRight, Check, ChevronDown, Clipboard, Download, Film, Headphones, Link as LinkIcon, Loader2, Music2, Plus, Settings2, X, CircleHelp, RefreshCw, Trash2, Pause, Play, HardDrive } from "lucide-react";
const ENGINE = "http://127.0.0.1:8941";
type Media = { url: string; title: string; author: string; duration: number; thumbnail: string; platform: string; heights: number[] };
type Job = { id: string; title: string; url: string; format: string; state: string; percent: number; message: string; filename?: string; bytes?: number; download?: string; created: number; thumbnail?: string };
const clock = (n: number) => Math.floor(n / 60) + ":" + String(Math.floor(n % 60)).padStart(2, "0");
const size = (n = 0) => n > 1048576 ? (n / 1048576).toFixed(1) + " MB" : Math.round(n / 1024) + " KB";
function Mark({ small = false }: { small?: boolean }) { return <span className={"brand-mark" + (small ? " small" : "")} aria-hidden="true"><span /><span /><span /><span /></span>; }
function RecordArt() {
  const bars = Array.from({ length: 38 }, (_, i) => 8 + Math.abs(Math.sin(i * 1.73) * Math.cos(i * .28)) * 39);
  return <div className="record-art" aria-hidden="true"><div className="art-caption"><span>THE INTERNET, OFFLINE.</span><span>VOL. 001</span></div><div className="record"><div className="record-label"><Mark small /><span>SAVE SOMETHING<br />GOOD.</span><i /></div></div><div className="tape"><div className="tape-top"><span>REEL / SOUND DEPARTMENT</span><span>90</span></div><div className="wave">{bars.map((h, i) => <i key={i} style={{ height: h }} />)}</div><div className="tape-bottom"><span>SIDE A</span><span>HIGH FIDELITY ↗</span></div></div><span className="art-sticker">ON<br />REPEAT.</span></div>;
}
export default function Home() {
  const [url, setUrl] = useState("");
  const [mode, setMode] = useState<"single" | "batch">("single");
  const [format, setFormat] = useState("mp4");
  const [quality, setQuality] = useState("1080");
  const [audioQuality, setAudioQuality] = useState("192");
  const [mono, setMono] = useState(false);
  const [connected, setConnected] = useState<boolean | null>(null);
  const [media, setMedia] = useState<Media | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [jobs, setJobs] = useState<Job[]>([]);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const [historyFilter, setHistoryFilter] = useState("all");
  const [modal, setModal] = useState<"settings" | "help" | null>(null);
  const [toast, setToast] = useState("");
  const [playing, setPlaying] = useState<string | null>(null);
  const [session, setSession] = useState("");
  const input = useRef<HTMLInputElement | HTMLTextAreaElement | null>(null);
  const audio = useRef<HTMLAudioElement | null>(null);
  const dialog = useRef<HTMLDialogElement | null>(null);
  async function checkEngine() {
    try { const r = await fetch(ENGINE + "/api/health", { signal: AbortSignal.timeout(3000) }); const d = await r.json() as {ready: boolean; session?: string}; setConnected(r.ok && d.ready === true); if (d.session) setSession(d.session); } catch { setConnected(false); }
  }
  useEffect(() => {
    checkEngine(); const timer = setInterval(checkEngine, 15000);
    try { const saved = JSON.parse(localStorage.getItem("reel-history") || "[]"); if (Array.isArray(saved)) setJobs(saved.filter(j => typeof j.id === "string" && typeof j.title === "string").slice(0, 30)); } catch {}
    setHistoryLoaded(true); return () => clearInterval(timer);
  }, []);
  useEffect(() => { if (!historyLoaded) return; try { localStorage.setItem("reel-history", JSON.stringify(jobs.slice(0, 30))); } catch {} }, [jobs, historyLoaded]);
  useEffect(() => { if (modal) dialog.current?.showModal(); else dialog.current?.close(); }, [modal]);
  useEffect(() => { if (!toast) return; const t = setTimeout(() => setToast(""), 3800); return () => clearTimeout(t); }, [toast]);
  const activeIds = jobs.filter(j => !["complete", "error", "expired"].includes(j.state)).map(j => j.id).join(",");
  useEffect(() => {
    if (!activeIds || !connected) return; let stopped = false;
    const update = async () => { await Promise.all(activeIds.split(",").map(async id => {
      try { const r = await fetch(ENGINE + "/api/jobs/" + id, { signal: AbortSignal.timeout(5000) });
        if (r.status === 404) { if (!stopped) setJobs(old => old.map(j => j.id === id ? { ...j, state: "expired", message: "Previous session. Paste the link to download again." } : j)); return; }
        if (!r.ok) return; const job = await r.json() as Job; if (!stopped) setJobs(old => old.map(j => j.id === id ? { ...j, ...job } : j));
      } catch {}
    })); };
    update(); const timer = setInterval(update, 1200); return () => { stopped = true; clearInterval(timer); };
  }, [activeIds, connected]);
  useEffect(() => () => { audio.current?.pause(); }, []);
  async function api<T>(path: string, body: object): Promise<T> {
    const r = await fetch(ENGINE + path, { method: "POST", headers: { "Content-Type": "application/json", "X-Reel-Session": session }, body: JSON.stringify(body), signal: AbortSignal.timeout(120000) });
    const d = await r.json() as T & {error?: string}; if (!r.ok) throw new Error(d.error || "Something went wrong. Please try again."); return d;
  }
  function validate(value: string) { try { const u = new URL(value); return ["https:", "http:"].includes(u.protocol) && ["youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be", "www.tiktok.com", "tiktok.com", "vm.tiktok.com", "vt.tiktok.com", "m.tiktok.com"].includes(u.hostname) && !u.username && !u.password; } catch { return false; } }
  async function inspect(e: React.FormEvent) {
    e.preventDefault(); setError(""); const urls = [...new Set(url.split(/\s+/).map(s => s.trim()).filter(Boolean))];
    if (!urls.length || urls.some(u => !validate(u))) { setError("Add a valid YouTube or TikTok video link."); input.current?.focus(); return; }
    if (urls.length > (mode === "batch" ? 5 : 1)) { setError(mode === "batch" ? "Keep each batch to 5 links." : "Use Batch links to add more than one video."); return; }
    if (!connected) { setModal("settings"); return; } setBusy(true); setMedia(null);
    try {
      if (mode === "batch") { const added: Job[] = [];
        for (const link of urls) { try { const j = await api<Job>("/api/jobs", { url: link, format, quality: format === "mp4" ? quality : audioQuality, mono }); added.push(j); setJobs(old => [j, ...old].slice(0, 30)); } catch (err) { setError((err as Error).message); break; } }
        if (added.length) { setToast(added.length + " download" + (added.length > 1 ? "s" : "") + " added to your desk."); document.getElementById("downloads")?.scrollIntoView({ behavior: "smooth", block: "start" }); }
      } else { setMedia(await api<Media>("/api/inspect", { url: urls[0] })); }
    } catch (err) { setError((err as Error).message === "Failed to fetch" ? "The download engine is unavailable. Open Connection to reconnect." : (err as Error).message); } finally { setBusy(false); }
  }
  async function download() {
    if (!media || busy) return; setBusy(true); setError("");
    try { const job = await api<Job>("/api/jobs", { url: media.url, format, quality: format === "mp4" ? quality : audioQuality, mono, title: media.title }); setJobs(old => [{ ...job, thumbnail: media.thumbnail }, ...old].slice(0, 30)); setToast("On it. Your download is on the desk."); document.getElementById("downloads")?.scrollIntoView({ behavior: "smooth", block: "start" }); } catch (err) { setError((err as Error).message); } finally { setBusy(false); }
  }
  async function paste() { try { setUrl(await navigator.clipboard.readText()); setMedia(null); setError(""); input.current?.focus(); } catch { input.current?.focus(); setToast("Press Ctrl+V (or ⌘V) to paste your link."); } }
  async function save(job: Job) {
    try { const r = await fetch(ENGINE + "/api/jobs/" + job.id); if (!r.ok) throw new Error("That file is no longer on this device. Download it again from the original link."); const current = await r.json() as Job; if (!current.download) throw new Error("This file is not ready yet."); const a = document.createElement("a"); a.href = ENGINE + current.download; a.download = current.filename || ""; a.click(); } catch (err) { setToast((err as Error).message); }
  }
  function preview(job: Job) {
    audio.current?.pause(); if (playing === job.id) { setPlaying(null); return; }
    const player = new Audio(ENGINE + job.download); audio.current = player; player.onended = () => setPlaying(null); player.onerror = () => { setPlaying(null); setToast("Preview unavailable. The file may belong to a previous session."); };
    player.play().then(() => setPlaying(job.id)).catch(() => { setPlaying(null); setToast("Couldn't play this file."); });
  }
  const visibleJobs = jobs.filter(j => historyFilter === "all" || j.format === historyFilter);
  const activeCount = jobs.filter(j => !["complete", "error", "expired"].includes(j.state)).length;
  return <div className="site-shell">
    <header className="site-header"><a className="brand" href="#" aria-label="REEL home"><Mark /><span>reel<span className="brand-dot">®</span></span></a><nav aria-label="Main navigation"><a className="nav-current" href="#converter">Downloader</a><a href="#downloads">Your downloads {activeCount > 0 && <b>{activeCount}</b>}</a><button onClick={() => setModal("help")}>How it works <ArrowUpRight size={14} /></button></nav><button className="connection" onClick={() => setModal("settings")}><span className={"status-dot " + (connected ? "online" : "")} />{connected === null ? "Connecting" : connected ? "Engine online" : "Connect engine"}<Settings2 size={15} /></button></header>
    <main>
      <section className="hero" aria-labelledby="hero-title"><div className="hero-copy"><div className="eyebrow"><span className="tiny-cross">✳</span> YOUR LITTLE CORNER OF THE INTERNET</div><h1 id="hero-title">Good finds.<br /><span>Yours to keep.</span></h1><p>The video you’ll watch again. The track you can’t shake.<br className="desktop-break" /> Save it from YouTube or TikTok, in a format that’s yours.</p><div className="platforms"><span><svg viewBox="0 0 24 18" width="22" aria-hidden="true"><rect x="0" y="1" width="24" height="16" rx="5" fill="currentColor" /><path d="m10 5 6 4-6 4Z" fill="#f6f3eb" /></svg>YouTube</span><i>+</i><span><Music2 size={20} strokeWidth={2.7} />TikTok</span><span className="platform-note">ONE LINK. ALL YOURS.</span></div></div><RecordArt /></section>
      <section id="converter" className="converter" aria-label="Video downloader">
        <div className="converter-top"><div className="tabs"><button className={mode === "single" ? "selected" : ""} onClick={() => { setMode("single"); setMedia(null); setError(""); }}><LinkIcon size={16} />Single link</button><button className={mode === "batch" ? "selected" : ""} onClick={() => { setMode("batch"); setMedia(null); setError(""); }}><Plus size={17} />Batch links<span className="new-tag">UP TO 5</span></button></div><span className="private-label"><HardDrive size={14} />Straight to your device</span></div>
        <form onSubmit={inspect}><label className="input-label" htmlFor="video-url">{mode === "single" ? "Got something good? Drop the link." : "A few good finds? One link per line."}</label><div className={"link-row " + (mode === "batch" ? "batch-row" : "")}><LinkIcon className="input-icon" size={21} />{mode === "single" ? <input id="video-url" ref={el => { input.current = el; }} value={url} onChange={e => { setUrl(e.target.value); setMedia(null); setError(""); }} placeholder="Paste a YouTube or TikTok link here…" autoComplete="off" spellCheck={false} /> : <textarea id="video-url" ref={el => { input.current = el; }} value={url} onChange={e => { setUrl(e.target.value); setError(""); }} placeholder={"https://youtube.com/watch?v=...\nhttps://tiktok.com/@creator/video/..."} rows={3} spellCheck={false} />}<button type="button" className="paste-btn" onClick={paste}><Clipboard size={16} />Paste</button><button className="fetch-btn" type="submit" disabled={busy}>{busy ? <><Loader2 className="spin" size={18} />Working</> : <>{mode === "single" ? "Find my video" : "Start batch"}<ArrowRight size={19} /></>}</button></div>
        <div className="options-row"><div className="format-pick" role="group" aria-label="Download format"><span>SAVE AS</span><button type="button" aria-pressed={format === "mp4"} className={format === "mp4" ? "active" : ""} onClick={() => setFormat("mp4")}><Film size={16} />Video <b>MP4</b>{format === "mp4" && <Check size={14} />}</button><button type="button" aria-pressed={format === "mp3"} className={format === "mp3" ? "active" : ""} onClick={() => setFormat("mp3")}><Headphones size={16} />Audio <b>MP3</b>{format === "mp3" && <Check size={14} />}</button></div><div className="quality-control"><label htmlFor="quality">{format === "mp4" ? "UP TO" : "QUALITY"}</label><select id="quality" value={format === "mp4" ? quality : audioQuality} onChange={e => format === "mp4" ? setQuality(e.target.value) : setAudioQuality(e.target.value)}>{format === "mp4" ? <><option value="2160">4K · 2160p</option><option value="1080">Full HD · 1080p</option><option value="720">HD · 720p</option><option value="480">Small · 480p</option></> : <><option value="320">320 kbps</option><option value="192">192 kbps</option><option value="128">128 kbps</option></>}</select><ChevronDown size={13} /></div></div>{format === "mp3" && <label className="mono-control"><input type="checkbox" checked={mono} onChange={e => setMono(e.target.checked)} /><span>Same sound in both ears</span><small>Mix to dual mono</small></label>}</form>
        {error && <div role="alert" className="error-message"><CircleHelp size={17} />{error}<button aria-label="Dismiss error" onClick={() => setError("")}><X size={16} /></button></div>}
        {media && <div className="media-result"><div className="media-thumb">{media.thumbnail ? <img src={media.thumbnail} alt="" /> : <Film />}<span>{clock(media.duration)}</span></div><div className="media-info"><span>{media.platform} <i>·</i> {media.author || "Video ready"}</span><h2>{media.title}</h2><p>{format === "mp4" ? "Best available quality up to " + (quality === "2160" ? "4K" : quality + "p") : "MP3 audio · " + audioQuality + " kbps" + (mono ? " · Both ears balanced" : "")}</p></div><button className="dark-btn" onClick={download} disabled={busy}>{busy ? <Loader2 className="spin" size={16} /> : <Download size={17} />}Download {format.toUpperCase()}</button></div>}
        <div className="converter-foot"><span><Check size={13} /> No ads. No detours.</span><span><Check size={13} /> MP4 + MP3</span><span><Check size={13} /> Quality you choose</span><span className="shortcut">PASTE. PICK. KEEP.</span></div>
      </section>
      <section id="downloads" className="downloads-section" aria-labelledby="downloads-title"><div className="section-heading"><div><span className="section-kicker">THE KEEP PILE</span><h2 id="downloads-title">Your download desk<span className="count">{jobs.length.toString().padStart(2, "0")}</span></h2></div><div className="history-tools"><div className="history-filters" role="group" aria-label="Filter downloads">{["all", "mp4", "mp3"].map(f => <button key={f} aria-pressed={historyFilter === f} className={historyFilter === f ? "active" : ""} onClick={() => setHistoryFilter(f)}>{f === "all" ? "All files" : f === "mp4" ? "Video" : "Audio"}</button>)}</div>{jobs.some(j => ["complete", "error", "expired"].includes(j.state)) && <button className="icon-btn" title="Clear finished history" aria-label="Clear finished history" onClick={() => { audio.current?.pause(); setPlaying(null); setJobs(j => j.filter(x => !["complete", "error", "expired"].includes(x.state))); }}><Trash2 size={16} /></button>}</div></div>
        <div className="download-list">{!visibleJobs.length ? <div className="empty-desk"><div className="empty-icon"><ArrowDown size={26} /><span /></div><div><h3>{jobs.length ? "Nothing in this format. Yet." : "Your next favorite belongs here."}</h3><p>{jobs.length ? "Try another filter or save a new find." : "Paste a link above. We’ll take it from there."}</p></div><span className="empty-aside">A LITTLE LESS SCROLLING.<br />A LITTLE MORE KEEPING.</span></div> : visibleJobs.map(job => <div className="download-item" key={job.id}><div className={"file-icon " + job.format}>{job.format === "mp4" ? <Film size={21} /> : <Headphones size={21} />}</div><div className="download-detail"><h3>{job.title}</h3><p><span className="format-label">{job.format.toUpperCase()}</span><span>{job.state === "complete" ? size(job.bytes) : job.message || "Queued"}</span>{job.state === "complete" && <span className="ready-text"><Check size={12} />Ready</span>}</p>{!["complete", "error", "expired"].includes(job.state) && <div className="progress-track" aria-label={job.message} role="progressbar" aria-valuenow={Math.round(job.percent)} aria-valuemin={0} aria-valuemax={100}><span style={{ width: job.percent + "%" }} /></div>}{["error", "expired"].includes(job.state) && <button className="retry-link" onClick={() => { setUrl(job.url); setMode("single"); setFormat(job.format); document.getElementById("converter")?.scrollIntoView({ behavior: "smooth" }); input.current?.focus(); }}><RefreshCw size={12} />Try this link again</button>}</div><div className="download-actions">{job.state === "complete" ? <>{job.format === "mp3" && <button className="icon-btn" aria-label={playing === job.id ? "Pause audio preview" : "Play audio preview"} onClick={() => preview(job)}>{playing === job.id ? <Pause size={17} /> : <Play size={17} />}</button>}<button className="save-btn" onClick={() => save(job)}>Save file<ArrowDown size={15} /></button></> : !["error", "expired"].includes(job.state) ? <span className="job-progress"><Loader2 size={16} className="spin" />{Math.round(job.percent)}%</span> : <span className="error-label">Needs a retry</span>}</div></div>)}</div><p className="history-note"><HardDrive size={12} />History stays in this browser. Files are available while your engine session is running.</p>
      </section>
      <section className="bottom-strip"><div><span className="strip-number">01 /</span><h3>Find your thing.</h3><p>Videos, tracks, tutorials. You know the one.</p></div><ArrowRight className="strip-arrow" size={22} /><div><span className="strip-number">02 /</span><h3>Make it yours.</h3><p>Pick MP4 for the picture. MP3 for the sound.</p></div><ArrowRight className="strip-arrow" size={22} /><div><span className="strip-number">03 /</span><h3>Take it offline.</h3><p>Save the file. Enjoy it on your own time.</p></div><span className="strip-star" aria-hidden="true">✳</span></section>
    </main>
    <footer><a className="footer-brand" href="#"><Mark small />reel</a><span>GOOD FINDS DESERVE A SECOND PLAY.</span><div><button onClick={() => setModal("help")}>A few useful things <ArrowUpRight size={13} /></button><span>© {new Date().getFullYear()} REEL</span></div></footer>
    <dialog ref={dialog} className="reel-dialog" onCancel={() => setModal(null)} onClick={e => { if (e.target === e.currentTarget) setModal(null); }}><div className="dialog-body"><button className="dialog-close icon-btn" aria-label="Close dialog" onClick={() => setModal(null)}><X size={21} /></button><span className="section-kicker">{modal === "settings" ? "THE ENGINE ROOM" : "A FEW USEFUL THINGS"}</span><h2>{modal === "settings" ? "A little power.\nOn your device." : "From link to keeper."}</h2>{modal === "settings" ? <><p>REEL pairs with a small local engine to fetch videos and convert audio. Your files stay on your computer.</p><div className="engine-status"><span className={"status-dot " + (connected ? "online" : "")} /><strong>{connected ? "Connected and ready" : "Engine is not connected"}</strong><button className="icon-btn" aria-label="Retry engine connection" onClick={checkEngine}><RefreshCw size={16} /></button></div><a className="dark-btn full" href="/reel-engine.zip" download><Download size={16} />Download engine for Windows</a><ol className="setup-list"><li>Download and unzip the REEL engine folder.</li><li>Run <code>start-reel.cmd</code> to start the engine.</li><li>Keep its window open while downloading. Allow local-network access if your browser asks.</li></ol><p className="dialog-note">Using a different device? Run the included engine there first. This site connects to the computer you’re browsing on.</p><button className="dark-btn full" onClick={checkEngine}><RefreshCw size={16} />Check connection</button></> : <><div className="help-step"><b>01</b><div><h3>Copy a public video link.</h3><p>YouTube videos, Shorts and TikTok video links are supported. Paste one link, or up to five in Batch links.</p></div></div><div className="help-step"><b>02</b><div><h3>Choose picture or sound.</h3><p>MP4 keeps the video. MP3 keeps the audio. Quality is limited by the original upload; a higher setting won’t invent extra detail.</p></div></div><div className="help-step"><b>03</b><div><h3>Make room for the good stuff.</h3><p>Start the download, then hit Save file when it’s ready. MP3 has an optional “same sound in both ears” setting.</p></div></div><p className="dialog-note">Public videos only. Private, paid, DRM-protected and live content isn’t supported. Some videos may be unavailable because of platform or region restrictions. Download content you own or have permission to save.</p><button className="dark-btn full" onClick={() => { setModal(null); input.current?.focus(); }}>Let’s find something <ArrowRight size={17} /></button></>}</div></dialog>
    {toast && <div className="toast" role="status"><Check size={16} />{toast}<button aria-label="Dismiss notification" onClick={() => setToast("")}><X size={15} /></button></div>}
  </div>;
}
