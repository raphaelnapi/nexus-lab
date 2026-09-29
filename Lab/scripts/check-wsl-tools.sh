#!/usr/bin/env bash
set -u

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd "$script_dir/../.." && pwd -P)"
manifest="${1:-$repo_root/wsl-requirements.txt}"

if [[ ! -r "$manifest" ]]; then
  printf 'ERROR: unreadable manifest: %s\n' "$manifest" >&2
  exit 2
fi

printf 'id\tcommand\tstatus\tpath\tmethod\tpackage\tinstalled_version\tcandidate_version\tcategory\tprofile\n'
while IFS=$'\t' read -r id command method package category profile notes; do
  [[ -z "${id:-}" || "$id" == \#* ]] && continue
  if path="$(command -v "$command" 2>/dev/null)"; then
    status="INSTALLED"
  else
    status="MISSING"
    path="-"
  fi
  installed_version="-"
  candidate_version="-"
  if [[ "$method" == "apt" ]]; then
    if command -v dpkg-query >/dev/null 2>&1; then
      installed_version="$(dpkg-query -W -f='${Version}' "$package" 2>/dev/null || printf '-')"
    fi
    if command -v apt-cache >/dev/null 2>&1; then
      candidate_version="$(apt-cache policy "$package" 2>/dev/null | awk '/^[[:space:]]*Candidate:/ { print $2; exit }')"
      [[ -n "$candidate_version" ]] || candidate_version="-"
    fi
  fi
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$id" "$command" "$status" "$path" "$method" "$package" \
    "$installed_version" "$candidate_version" "$category" "$profile"
done < "$manifest"
