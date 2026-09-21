# Vertical-video UHD upscale

`upscale_uhd.sh` upscales a heavily-compressed portrait phone video to vertical 4K
(2160x3840) using only ffmpeg filters — no neural network, no hallucinated detail.

```bash
FFMPEG=/path/to/ffmpeg ./upscale_uhd.sh input.mp4 output.mp4 16
```

Requires an ffmpeg built with `libx264`, `zimg` (for `zscale`), and the `guided`,
`deblock` and `cas` filters. Defaults to `ffmpeg` on `PATH`; override with `$FFMPEG`.

## Why this chain

Every choice below was measured on the source it was built for (1024x576 stored with
a -90 display matrix, i.e. 576x1024 portrait, H.264 **Baseline** at 661 kb/s, 809
frames @ 29.96 fps). Four pipelines were built and scored blind against a
bicubic control on three axes — facial naturalness, false detail, and temporal
stability. Notes below are the findings that survived verification.

### The dominant damage is chroma, not luma

58% of Cr and 70% of Cb 8x8 blocks in the source are **flat constants**; chroma
high-frequency energy sits 20-30x below luma. At 3.75x those blocks become ~60px
solid colour tiles — this is the green/magenta speckle visible in grey hair.

The fix is a luma-guided filter over each chroma plane, which re-attaches colour to
real luma edges. `radius=8` spans the chroma block; `eps=0.001` keeps it pinned to
genuine detail so specular highlights survive. This is the single largest visible
improvement in the whole chain, and it is a real restoration rather than invention.

> `guided` takes its inputs as `[guide][source]` — the reverse of the intuitive
> order. Wired the other way it silently filters luma using chroma as the guide and
> writes the result into U/V; the output goes magenta/green with no error.

### Sharpen before the upscale, not after

`cas` is a 3x3 kernel, so it has no leverage once the image is 3.75x larger. Applied
before the resize at `strength=0.35`, the output — resampled back down to source
scale — matches source detail at a high-pass std ratio of **0.991**. That is the
target: restoration to transparency, not beyond it.

### `zscale d=ordered` stamps a Nyquist checkerboard

Measured **278:1** FFT peak-to-median at (0.5, 0.5) cyc/px in flat regions, and it
costs ~11% extra bitrate encoding its own dither pattern. `d=none` measures 1.7:1.

This defect is invisible in still-frame testing — writing PNG, `d=ordered` and
`d=none` are byte-identical (same md5). The dither only engages on the video path's
16-bit to 8-bit yuv420p conversion. Test resampler dither on the *encode* path.

### Things that measured worse and were removed

- **`deband` / `gradfun`** — the flat-area defect here is 8x8 DC plateaus, not
  gradient contouring, so these are the wrong tool. `deband` worsened the block
  metric (0.488 -> 0.597) and its dither is visible as grain across flat areas.
- **Temporal denoise** (`hqdn3d`, `atadenoise`) — the source has no static content
  and optical flow p90 of 13 px/frame. Temporal filtering only ghosts on handheld
  footage. It degraded both the traditional and the neural route.
- **`nnedi` as a 2x upscaler** — scored VMAF 75.55 against lanczos3's 82.40 while
  running 3x slower. Its Laplacian variance is *higher* while fidelity is *lower*,
  i.e. it manufactures high-frequency detail absent from the reference — which on a
  compressed source means committing to codec artifact edges.
- **Staged upscaling** (576->1152->2160) — a dead heat with one-shot (VMAF 82.37 vs
  82.40), so one-shot wins on fewer resamples.
- **lanczos `a=4`** — wins PSNR (37.66 vs 37.54) but loses VMAF (82.04 vs 82.40);
  the extra taps add ringing that fidelity metrics reward and perception punishes.

### Why not a neural upscaler

Real-ESRGAN `realesr-general-x4v3` was implemented and benchmarked (SRVGGNetCompact,
1.2M params, 7.2 s/frame on 4 CPU cores). It genuinely won on texture — +28% in-band
sequin energy, 8.0px edge rise against 12-13px for every other route, and no invented
flecks or lattice.

It was still rejected, because on **sharp** frames it produces exactly the failure
this content cannot afford: grey hair collapses into a waxy plastic mass with all
strand structure gone, the hairline against the background becomes a hard cut-out
edge, and foreheads lose all grain. Its apparent detail gain is manufactured edge
contrast, not recovered texture — skin micro-texture measured 0.104 against a source
0.475 on the jaw (-78%) while the forehead read +48%, i.e. redistribution. It also
measured 1.8-2.2x the control's temporal flicker on genuinely frozen content, since
per-frame inference re-decides each frame independently.

For faces of real people, a slightly softer result that still reads as a photograph
beats a sharper one that reads as a render.

> Benchmark on **sharp** frames. An early test segment chosen for "faces + motion"
> had median Laplacian variance 51.8 against the video's 74.6 — motion means blur,
> and blurred frames hide precisely the plastic-skin artifact that decides this.

### Delivery encode

x264 CRF 16, High profile, yuv420p, bt709, `+faststart`. H.265 would be ~2x more
efficient, but x265 at CRF 18 was measured re-deciding flat-CTU quantisation frame to
frame — visible as boiling in static areas — and H.264 plays everywhere.

Audio is **stream-copied**, never re-encoded; the output audio is bit-identical to
the source (verified by md5 of the extracted ADTS stream).

`-metadata:s:v rotate=0` is required, or the source's -90 display matrix is carried
into the output and applied a second time on playback.
