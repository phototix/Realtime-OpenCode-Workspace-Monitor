#!/usr/bin/env bash

set -euo pipefail

commit_message="${1:-update}"

git add -A
git commit -m "$commit_message"
git push