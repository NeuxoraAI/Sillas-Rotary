# Asset Optimization

New videos under `front/assets/video/` are not optimized automatically. Optimize them locally before referencing them from HTML.

## Videos

Use the project helper:

```bash
scripts/optimize-video.sh "front/assets/video/my video.mov"
```

Without an output path, the script writes an optimized copy beside the source as `<basename>.optimized.mp4` and keeps the original untouched.

To intentionally replace the app-used login video after visual review, run the script against the local source video you want to ship:

```bash
scripts/optimize-video.sh \
  "/path/to/source/VIDEOLOGIN.mp4" \
  "front/assets/video/VIDEOLOGIN.mp4"
```

Issue #45 baseline for the login video: `5.1M` original to `836K` optimized using `480p` max height, `24fps`, `CRF 34`, `libx264`, `yuv420p`, `faststart`, and no audio.

Always do manual visual QA on mobile and desktop before shipping a new optimized video.
