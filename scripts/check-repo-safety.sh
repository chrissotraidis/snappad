#!/usr/bin/env bash
set -euo pipefail

SNAPPAD_AUDIT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$SNAPPAD_AUDIT_ROOT"

fail() {
    printf 'Repository safety check failed: %s\n' "$*" >&2
    exit 1
}

current_files=$(git ls-files --cached --others --exclude-standard | sort -u)

tracked_ref=$(printf '%s\n' "$current_files" | grep '^ref/' || true)
[[ -z "$tracked_ref" ]] || { printf '%s\n' "$tracked_ref" >&2; fail "ref/ is publishable"; }

forbidden='(^|/)(generated|build-tools|logs|artifacts)(/|$)|\.(z64|n64|v64|rom|elf|sav|srm|fla|ipa|xcarchive|mobileprovision|provisionprofile|p12|p8|crash|ips)(/|$)|(^|/)[^/]+\.app/'
forbidden_files=$(printf '%s\n' "$current_files" | grep -Ei "$forbidden" || true)
[[ -z "$forbidden_files" ]] || { printf '%s\n' "$forbidden_files" >&2; fail "private or generated material is publishable"; }

personal_path='/''Users/[^/[:space:]]+|/private/var/''folders/'
while IFS= read -r file; do
    [[ -f "$file" ]] || continue
    if grep -nEI "$personal_path" "$file" >/dev/null 2>&1; then
        printf '%s\n' "$file" >&2
        fail "absolute personal path exists in publishable content"
    fi
done < <(printf '%s\n' "$current_files")

credential_pattern='(-----BEGIN [A-Z ]*PRIVATE KEY-----|github_pat_[A-Za-z0-9_]{20,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16})'
while IFS= read -r file; do
    [[ -f "$file" ]] || continue
    if grep -nEI "$credential_pattern" "$file" >/dev/null 2>&1; then
        printf '%s\n' "$file" >&2
        fail "likely credential or private key exists in publishable content"
    fi
done < <(printf '%s\n' "$current_files")

while IFS= read -r file; do
    [[ -f "$file" ]] || continue
    size=$(wc -c < "$file")
    (( size <= 5242880 )) || fail "$file exceeds the 5 MiB review limit"
done < <(printf '%s\n' "$current_files")

bash -n scripts/*.sh scripts/lib/*.sh
git diff --check
note='Repository safety checks passed.'
printf '%s\n' "$note"
