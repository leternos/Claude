#!/usr/bin/env bash
# Final UHD upscale: 576x1024 -> 2160x3840 (vertical 4K, exactly 3.75x)
#
# Chain rationale, all measured on this specific source:
#   - deblock weak/block=8 on LUMA ONLY: the H.264 Baseline 661 kb/s encode leaves
#     8x8 DC plateaus. Measured block-grid energy drops 1.219 -> 0.722 vs bicubic.
#   - guided-filter chroma reconstruction: THE key restoration. 58% of Cr and 70% of
#     Cb 8x8 blocks are flat constants in the source; at 3.75x those become ~60px
#     solid colour tiles (the rainbow speckle visible in grey hair). Luma guides the
#     chroma so colour re-attaches to real edges. radius=8 spans the chroma block,
#     eps=0.001 keeps it pinned to luma detail.
#     NOTE: ffmpeg's `guided` takes inputs as [guide][source] - reversed order
#     silently filters luma by chroma and outputs magenta/green with no error.
#   - NO deband/gradfun: the flat-area defect here is DC plateaus, not gradient
#     contouring, so those are the wrong tool and both measured worse.
#   - NO temporal denoise (hqdn3d/atadenoise): measured zero static content and
#     optical flow p90 of 13 px/frame. Temporal filtering only ghosts on this
#     handheld footage, and it demonstrably degraded the neural route too.
#   - cas=0.35 before the upscale: a 3x3 sharpener has no leverage after 3.75x.
#     Tuned so the output, resampled back to source scale, matches source detail
#     (hp_std ratio 0.991) - restoration to transparency, not invention.
#   - zscale spline36 with d=none: d=ordered stamps a Nyquist checkerboard,
#     measured 278:1 peak/median on the video path, and costs 11% extra bitrate
#     encoding its own dither. d=none measures 1.7:1.
#   - 10/16-bit throughout so filter stages do not compound banding; dither to
#     8-bit only at the very end.
#   - x264 CRF 16 High profile: temporally stable (x265 CRF18 was measured
#     re-deciding flat CTU quantisation frame-to-frame, visible as boiling) and
#     universally playable. Audio stream-copied bit-identical, never re-encoded.
#   - -metadata:s:v rotate=0 so the source's -90 display matrix is not carried
#     through and double-applied on playback.
set -euo pipefail

SP="$(cd "$(dirname "$0")" && pwd)"
FF="${FFMPEG:-ffmpeg}"
IN="${1:?usage: upscale_uhd.sh <input.mp4> [output.mp4] [crf]}"
OUT="${2:-upscaled_4k.mp4}"
CRF="${3:-16}"
mkdir -p "$(dirname "$OUT")"

CHAIN="[0:v]format=yuv420p10le,\
deblock=filter=weak:block=8:planes=1,\
format=yuv444p16le,\
extractplanes=y+u+v[y][u][v];\
[y]split=3[yo][g1][g2];\
[g1][u]guided=guidance=on:planes=1:radius=8:eps=0.001[u2];\
[g2][v]guided=guidance=on:planes=1:radius=8:eps=0.001[v2];\
[yo][u2][v2]mergeplanes=0x001020:yuv444p16le,\
cas=strength=0.35,\
zscale=w=2160:h=3840:f=spline36:d=none,\
format=yuv420p[vout]"

echo "[final] $IN -> $OUT (CRF $CRF)"
time "$FF" -hide_banner -stats -y -threads 4 -i "$IN" \
  -filter_complex "$CHAIN" \
  -map "[vout]" -map 0:a:0 \
  -c:v libx264 -preset slow -crf "$CRF" -pix_fmt yuv420p \
  -profile:v high -level 5.2 \
  -color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv \
  -c:a copy \
  -metadata:s:v rotate=0 -movflags +faststart \
  "$OUT"

echo "[final] done"
ls -la "$OUT"
