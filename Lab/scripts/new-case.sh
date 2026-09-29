#!/usr/bin/env bash
set -euo pipefail

usage() {
  printf 'Usage: %s CASE-YYYY-NNNN\n' "$0" >&2
  exit 2
}

[[ $# -eq 1 ]] || usage
case_id=$1
[[ "$case_id" =~ ^CASE-[0-9]{4}-[0-9]{4,}$ ]] || {
  printf 'Invalid case ID: %s\n' "$case_id" >&2
  usage
}

command -v sqlite3 >/dev/null 2>&1 || {
  printf 'Missing dependency: sqlite3 (installation requires explicit authorization).\n' >&2
  exit 3
}

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
root=$(cd -- "$script_dir/../.." && pwd -P)
case_dir="$root/Lab/cases/$case_id"
registry_dir="$root/Registry/$case_id"
schema="$root/Lab/database/schema.sql"

[[ -f "$schema" ]] || { printf 'Schema not found: %s\n' "$schema" >&2; exit 4; }
[[ ! -e "$case_dir" && ! -e "$registry_dir" ]] || {
  printf 'Refusing to overwrite an existing case: %s\n' "$case_id" >&2
  exit 5
}

mkdir -p -- \
  "$case_dir/00-administrative" \
  "$case_dir/01-working-copies" \
  "$case_dir/02-extracted" \
  "$case_dir/03-analysis" \
  "$case_dir/04-timelines" \
  "$case_dir/05-reports" \
  "$case_dir/06-exports" \
  "$case_dir/database" \
  "$case_dir/logs" \
  "$registry_dir"

db="$case_dir/database/case.sqlite3"
sqlite3 "$db" < "$schema"
opened_at=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
sqlite3 "$db" "INSERT INTO cases(case_id, opened_at_utc) VALUES('$case_id', '$opened_at');"

printf 'Created case %s\nDatabase: %s\nRegistry: %s\n' "$case_id" "$db" "$registry_dir"
