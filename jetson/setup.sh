#!/usr/bin/env bash
set -euo pipefail
source_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
install_base="${ENGINE_INSTALL_BASE:-$HOME/oned_device_bench}"
if [[ $# -ne 1 ]]; then
    echo 'Usage: bash jetson/setup.sh /dev/v4l/by-id/YOUR_CAMERA-video-index0' >&2
    exit 2
fi
if [[ "$(uname -s)" != Linux || "$(uname -m)" != aarch64 ]]; then
    echo 'Use Jetson Orin Nano with JetPack 6.2.x (TensorRT 10.3 / CUDA 12.6).' >&2
    exit 1
fi
for protected in current assets config data; do
    if [[ -e "$install_base/$protected" || -L "$install_base/$protected" ]]; then
        echo "Existing installation preserved: $install_base/$protected" >&2
        exit 1
    fi
done
python3.10 -B -X utf8 "$source_root/install.py" --check-only --base "$install_base" --camera "$1"
if [[ -e "$install_base/envs/app_v1" || -L "$install_base/envs/app_v1" ]]; then
    echo 'Existing Python environment preserved. Use INSTALL.md to resume preparation explicitly.' >&2
    exit 1
fi
python3.10 -m venv --system-site-packages "$install_base/envs/app_v1"
runtime_python="$install_base/envs/app_v1/bin/python"
"$runtime_python" -m pip install -r "$source_root/requirements-runtime.txt"
"$runtime_python" -B -X utf8 "$source_root/install.py" --base "$install_base" --camera "$1"
echo "Installed (stopped, MOCK). Start with:"
printf '"%s" -B -X utf8 "%s/current/manage_live.py" start --config "%s/config/runtime.json"\n' "$runtime_python" "$install_base" "$install_base"
