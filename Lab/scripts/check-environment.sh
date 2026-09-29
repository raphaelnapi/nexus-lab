#!/usr/bin/env bash
set -u

printf 'kernel\t%s\n' "$(uname -srmo 2>/dev/null || true)"
if grep -qi microsoft /proc/version 2>/dev/null; then
  printf 'wsl\tdetected\n'
else
  printf 'wsl\tnot detected\n'
fi

for tool in bash python3 sha256sum sha512sum findmnt lsblk blkid; do
  if command -v "$tool" >/dev/null 2>&1; then
    printf '%s\t%s\n' "$tool" "$(command -v "$tool")"
  else
    printf '%s\tMISSING\n' "$tool"
  fi
done

printf '\nCataloged forensic tools:\n'
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
bash "$script_dir/check-wsl-tools.sh"

printf '\nMounted filesystems under /mnt:\n'
findmnt -rn -o TARGET,FSTYPE,OPTIONS 2>/dev/null | awk '$1 ~ /^\/mnt(\/|$)/ { print }' || true

printf '\nThis check is read-only and does not install packages.\n'
