#!/usr/bin/env bash
set -euo pipefail

usage() {
  printf 'Usage: %s <input-video> [output-video]\n' "${0##*/}" >&2
}

fail() {
  printf 'Error: %s\n' "$1" >&2
  exit 1
}

file_size_bytes() {
  if stat -c '%s' "$1" >/dev/null 2>&1; then
    stat -c '%s' "$1"
  else
    stat -f '%z' "$1"
  fi
}

human_size() {
  if command -v numfmt >/dev/null 2>&1; then
    numfmt --to=iec --suffix=B "$1"
  else
    printf '%s bytes' "$1"
  fi
}

absolute_path() {
  local path=$1
  local dir
  local base

  dir=$(dirname -- "$path")
  base=$(basename -- "$path")
  (cd -- "$dir" && printf '%s/%s\n' "$(pwd -P)" "$base")
}

if [[ $# -lt 1 || $# -gt 2 ]]; then
  usage
  exit 2
fi

command -v ffmpeg >/dev/null 2>&1 || fail 'ffmpeg is required but was not found in PATH.'

input=$1
[[ -f "$input" ]] || fail "input video does not exist: $input"
original_size=$(file_size_bytes "$input")

if [[ $# -eq 2 ]]; then
  output=$2
else
  input_dir=$(dirname -- "$input")
  input_name=$(basename -- "$input")
  input_stem=${input_name%.*}
  output="$input_dir/$input_stem.optimized.mp4"
fi

output_dir=$(dirname -- "$output")
[[ -d "$output_dir" ]] || fail "output directory does not exist: $output_dir"

input_abs=$(absolute_path "$input")
output_abs=$(absolute_path "$output")
tmp_output=$(mktemp "${output_abs}.tmp.XXXXXX.mp4")

cleanup() {
  rm -f -- "$tmp_output"
}
trap cleanup EXIT

ffmpeg \
  -y \
  -i "$input_abs" \
  -vf 'scale=-2:480' \
  -r 24 \
  -c:v libx264 \
  -crf 34 \
  -an \
  -pix_fmt yuv420p \
  -movflags +faststart \
  "$tmp_output"

mv -f -- "$tmp_output" "$output_abs"
trap - EXIT

optimized_size=$(file_size_bytes "$output_abs")

printf 'Original:  %s (%s)\n' "$input_abs" "$(human_size "$original_size")"
printf 'Optimized: %s (%s)\n' "$output_abs" "$(human_size "$optimized_size")"

if [[ "$input_abs" == "$output_abs" ]]; then
  printf 'Replaced original only after successful optimization.\n'
fi
