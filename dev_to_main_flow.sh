#!/usr/bin/env bash
set -euo pipefail

# Configuration
PROJECT_DIR="/Users/khalfanalkindi/apps/dararab/work/dararab_app_backend_v01"
VENV_DIR="$PROJECT_DIR/.venv"

usage() {
  cat <<'USAGE'
Usage:
  ./dev_to_main_flow.sh run-local                # activate venv, migrate, runserver
  ./dev_to_main_flow.sh pull-develop             # checkout develop and pull latest
  ./dev_to_main_flow.sh push-develop "MSG"       # commit and push to develop
  ./dev_to_main_flow.sh merge-to-main            # merge develop -> main and push
  ./dev_to_main_flow.sh sync-develop-with-main   # merge main -> develop and push
USAGE
}

ensure_repo() {
  cd "$PROJECT_DIR"
  git rev-parse --is-inside-work-tree >/dev/null 2>&1 || {
    echo "Not a git repository: $PROJECT_DIR" >&2
    exit 1
  }
}

pull_develop() {
  ensure_repo
  git checkout develop
  git pull origin develop
}

run_local() {
  ensure_repo
  # Ensure venv
  if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
  fi
  # Activate and install deps
  # shellcheck disable=SC1090
  source "$VENV_DIR/bin/activate"
  python -m pip install --upgrade pip
  pip install -r requirements.txt
  # Migrate and run
  python manage.py migrate
  python manage.py runserver
}

push_develop() {
  ensure_repo
  local msg=${1:-"Update: changes from local testing"}
  git checkout develop
  git pull origin develop
  git add .
  git commit -m "$msg" || echo "No changes to commit."
  git push origin develop
}

merge_to_main() {
  ensure_repo
  git fetch origin
  git checkout main
  git pull origin main
  git merge --no-ff develop || {
    echo "Merge conflicts. Resolve, then: git add . && git commit && git push origin main" >&2
    exit 1
  }
  git push origin main
}

sync_develop_with_main() {
  ensure_repo
  git fetch origin
  git checkout develop
  git pull origin develop
  git merge --no-ff main || {
    echo "Merge conflicts. Resolve, then: git add . && git commit && git push origin develop" >&2
    exit 1
  }
  git push origin develop
}

cmd=${1:-}
case "$cmd" in
  run-local)
    run_local
    ;;
  pull-develop)
    pull_develop
    ;;
  push-develop)
    shift || true
    push_develop "$@"
    ;;
  merge-to-main)
    merge_to_main
    ;;
  sync-develop-with-main)
    sync_develop_with_main
    ;;
  *)
    usage
    exit 1
    ;;
 esac
