#!/usr/bin/env bash
set -u

usage() {
  printf 'Usage: %s --authorized TOOL_ID EXPECTED_VERSION [MANIFEST]\n' "${0##*/}" >&2
  printf 'Run only after the user explicitly authorizes the named package install and network access.\n' >&2
}

if [[ "${1:-}" != "--authorized" || -z "${2:-}" || -z "${3:-}" ]]; then
  usage
  exit 2
fi

tool_id="$2"
expected_version="$3"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd "$script_dir/../.." && pwd -P)"
manifest="${4:-$repo_root/wsl-requirements.txt}"

if ! grep -qi microsoft /proc/version 2>/dev/null; then
  printf 'ERROR: this installer must run inside WSL 2.\n' >&2
  exit 3
fi
if [[ ! -r "$manifest" ]]; then
  printf 'ERROR: unreadable manifest: %s\n' "$manifest" >&2
  exit 4
fi
if [[ ! -r /etc/os-release ]]; then
  printf 'ERROR: cannot identify the WSL distribution.\n' >&2
  exit 5
fi

# shellcheck disable=SC1091
. /etc/os-release
case "${ID:-}" in
  ubuntu|debian) ;;
  *)
    printf 'ERROR: unsupported distribution: %s. Review a distribution-specific method.\n' "${ID:-unknown}" >&2
    exit 6
    ;;
esac

record="$(awk -F '\t' -v wanted="$tool_id" '$1 == wanted { print; found=1; exit } END { if (!found) exit 1 }' "$manifest")" || {
  printf 'ERROR: unknown tool id: %s\n' "$tool_id" >&2
  exit 7
}
IFS=$'\t' read -r id command method package category profile notes <<< "$record"

if command -v "$command" >/dev/null 2>&1; then
  printf 'ALREADY_INSTALLED\t%s\t%s\n' "$id" "$(command -v "$command")"
  exit 0
fi
if [[ "$method" != "apt" ]]; then
  printf 'ERROR: %s uses method=%s. Prepare and authorize a separately reviewed installation plan.\n' "$id" "$method" >&2
  exit 8
fi
if ! command -v apt-get >/dev/null 2>&1; then
  printf 'ERROR: apt-get is unavailable.\n' >&2
  exit 9
fi
if ! command -v apt-cache >/dev/null 2>&1; then
  printf 'ERROR: apt-cache is unavailable; cannot verify the authorized version.\n' >&2
  exit 10
fi

candidate_version="$(apt-cache policy "$package" 2>/dev/null | awk '/^[[:space:]]*Candidate:/ { print $2; exit }')"
if [[ -z "$candidate_version" || "$candidate_version" == "(none)" ]]; then
  printf 'ERROR: no candidate version for %s in current apt metadata. Do not run apt-get update without separate authorization.\n' "$package" >&2
  exit 11
fi
if [[ "$candidate_version" != "$expected_version" ]]; then
  printf 'ERROR: candidate version changed: authorized=%s current=%s. Request renewed authorization.\n' "$expected_version" "$candidate_version" >&2
  exit 12
fi

log_dir="$repo_root/Lab/logs/tool-installations"
case "$log_dir/" in
  "$repo_root/Lab/"*) ;;
  *) printf 'ERROR: log path escaped Lab/: %s\n' "$log_dir" >&2; exit 13 ;;
esac
mkdir -p -- "$log_dir"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
log_path="$log_dir/${stamp}-${id}-$$.log"

{
  printf 'start_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf 'operator=%s\n' "${USER:-unknown}"
  printf 'distribution=%s\n' "${PRETTY_NAME:-${ID:-unknown}}"
  printf 'tool_id=%s\ncommand=%s\nmethod=%s\npackage=%s\nversion=%s\n' "$id" "$command" "$method" "$package" "$expected_version"
  printf 'install_command=sudo apt-get install --yes --no-install-recommends %s=%s\n' "$package" "$expected_version"
} > "$log_path"

printf 'Installing package %s for tool %s; log: %s\n' "$package" "$id" "$log_path"
sudo apt-get install --yes --no-install-recommends "$package=$expected_version" >> "$log_path" 2>&1
exit_status=$?
{
  printf 'exit_status=%s\n' "$exit_status"
  printf 'end_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} >> "$log_path"

if [[ $exit_status -ne 0 ]]; then
  printf 'ERROR: installation failed with status %s; review %s\n' "$exit_status" "$log_path" >&2
  exit "$exit_status"
fi
if ! resolved="$(command -v "$command" 2>/dev/null)"; then
  printf 'ERROR: package installed but expected command is unavailable: %s\n' "$command" >&2
  exit 14
fi
installed_version="$(dpkg-query -W -f='${Version}' "$package" 2>/dev/null || printf 'unknown')"
printf 'installed_version=%s\n' "$installed_version" >> "$log_path"
printf 'INSTALLED\t%s\t%s\t%s\n' "$id" "$resolved" "$log_path"
