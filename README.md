# OmniMimic project page

Public project website: **https://omnimimic.github.io/**

A dependency-free, responsive academic project page. GitHub Pages serves `main` from the repository root; `.nojekyll` disables Jekyll processing.

## Content

- Main 2×2 outdoor demo: Trot / Pace / Canter / Pronk.
- Eight additional real-world videos.
- Paper overview, selected simulation results, and the current framework figure.
- Anonymous presentation by default; no unpublished author details or manuscript source are included.

All videos show the supplied physical-robot recordings, at original playback speed. The shorter main-demo panels hold their final frame so the longest clip can finish. Audio is omitted in web exports. The original `.mov` recordings are not modified. The site provides a 1080p H.264 player and a separate 4K H.264 download of the main demo. Supplementary videos are 1080p H.264, with fast-start metadata and on-demand loading.

## Local preview

```sh
python3 -m http.server 8765 --bind 127.0.0.1
```

Open http://127.0.0.1:8765/ .

## Rebuild media

Requires Python, Pillow, FFmpeg, and ffprobe. Source folders are passed explicitly and are not committed to this repository.

```sh
python3 scripts/prepare_media.py --source-root /path/to/recordings --work-dir /path/to/temporary-work
```

`media-manifest.json` records source hashes, timing, layout, and export properties. It contains no account credentials.

## Credits

Project-page organization was inspired by [APEX](https://marmotlab.github.io/APEX/). The website implementation and OmniMimic assets are separate; no APEX videos, author details, or research claims are reused.

The repository hosts the website only. It is not a release of the policy-training implementation.
