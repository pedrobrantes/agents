---
name: cli-media-acquisition
description: 'Mastery of command-line tools for high-speed media downloading, streaming, and content discovery across the web without relying on Tor or complex torrent setups. Covers tools like yt-dlp, aria2, mov-cli, gallery-dl, and advanced scraping techniques.'
license: MIT
allowed-tools: Bash, Nix, yt-dlp, aria2c, mov-cli
---

# CLI Media Acquisition & Discovery

## Core Philosophy
Use lightweight, high-performance command-line tools to bypass bloated web interfaces, ads, and tracking while achieving maximum download speeds through multi-connection protocols.

## 1. The "Ultimate" Download Engine: yt-dlp + aria2
This combination is the CLI equivalent of IDM (Internet Download Manager) but more powerful and scriptable.

### Installation (Nix)
```nix
{ pkgs, ... }: {
  home.packages = [ pkgs.yt-dlp pkgs.aria2 ];
}
```

### High-Speed Aliases
```bash
# Video (Max quality, 16 connections, metadata embedded)
alias b="yt-dlp --downloader aria2c --downloader-args 'aria2c:-x 16 -s 16 -k 1M' --embed-metadata -f 'bestvideo+bestaudio/best' --merge-output-format mp4"

# Audio Only (MP3 conversion)
alias bmusic="yt-dlp -x --audio-format mp3 --downloader aria2c --downloader-args 'aria2c:-x 16 -s 16 -k 1M'"
```

## 2. Searching & Streaming: mov-cli
Browse movies and TV shows directly from the terminal.

### Usage
- **Search and Play:** `mov-cli "Interstellar"`
- **Specify Provider:** `mov-cli -s vidsrc "The Bear"` (vidsrc, sflix, and streamberry are common providers)
- **Select Episode:** Interactive menu follows the search.

## 3. Direct Download (DDL) Strategies
When streaming sites are slow, use Direct Download Links.

### Google Dorks (Open Directories)
Search for exposed server directories containing media:
`intitle:"index.of" (mp4|mkv|avi) "Movie Name" -html -htm -php -jsp`

### Advanced Download with aria2c
If you have a direct link, use aria2c directly for multi-segmented downloading:
```bash
aria2c -x 16 -s 16 -k 1M "https://example.com/very-large-movie.mkv"
```

## 4. Specialized Toolset (The "More" Part)

### Gallery-dl: For Images & Manga
Download entire galleries or manga chapters from sites like Imgur, Danbooru, or MangaDex.
```bash
gallery-dl "https://mangadex.org/title/..."
```

### Lux (formerly Annie): Fast & Simple
Supports major platforms (especially Asian sites) with extremely fast extraction.
```bash
lux -f 1080p "https://www.bilibili.com/video/..."
```

### Streamlink: For Live Content
Watch live streams (Twitch, YouTube Live) in `mpv` without the browser overhead.
```bash
streamlink "https://twitch.tv/streamer" best
```

### FFmpeg: Post-Processing
Merge subtitles, cut clips, or change formats without re-encoding (instant).
```bash
# Add external subtitle to video
ffmpeg -i video.mp4 -i subtitle.srt -c copy -c:s mov_text output.mp4

# Cut a clip (5:00 to 10:00)
ffmpeg -ss 00:05:00 -to 00:10:00 -i input.mp4 -c copy output.mp4
```

## 5. Bypassing Restrictions

### Proxychains-ng
If a site is geo-blocked, route your CLI tool through a SOCKS5 proxy/VPN:
```bash
proxychains4 yt-dlp "https://blocked-site.com/video"
```

### User-Agent Spoofing
If a site blocks CLI tools, mimic a real browser:
```bash
yt-dlp --user-agent "Mozilla/5.0 (Windows NT 10.0; Win64; x64)..." "URL"
```

## 6. Nix Integration Best Practices
Keep your tools declarative in your `home-manager` config.
1. Add packages to `programs/*.nix`.
2. Add aliases to `programs/bash.nix` or `programs/zsh.nix`.
3. Run `home-manager switch` to apply.

## Summary Table
| Goal | Tool |
|------|------|
| General Video | `yt-dlp` |
| Speed Engine | `aria2c` |
| Movies/Series | `mov-cli` |
| Animes | `ani-cli` |
| Live Streams | `streamlink` |
| Manga/Images | `gallery-dl` |
| Formats/Subs | `ffmpeg` |
