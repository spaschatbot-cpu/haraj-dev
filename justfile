# Every command a person needs on this project, in one place.
#
#   just            list the commands
#   just setup      first run after a clone
#   just up         start PostgreSQL and Redis
#   just test       the suite, on PostgreSQL
#   just lint       ruff + the constitutional guards (mypy: just lint-types)
#   just migrate    apply migrations
#   just run        the development server
#   just verify     recompute the ledger and report every disagreement
#
# Why a justfile and not a Makefile: `make` treats every recipe name as a file
# it might already have built, and on Windows it is not installed at all. This
# is a list of commands with names, and nothing more.
#
# Install just once: `uv tool install rust-just`, or see https://just.systems.
#
# Every recipe line is a single command with no `&&`, no `||` and no shell
# builtins, and directories are changed with `[working-directory]` rather than
# with `cd`. The reason is that just runs recipes through `sh` on Unix and
# `cmd` on Windows, and the two agree on almost nothing. Anything that needed
# real shell logic is written as a one-line Python call through `uv run`, which
# is the one interpreter guaranteed to be present on every machine here.

# just looks for `sh` on Windows too, and a plain Git for Windows install does
# not put one on PATH — so it is named explicitly rather than left to whether a
# particular developer happens to have Git Bash exported. Every recipe here is
# written to run unchanged under both `sh` and `cmd`.
set windows-shell := ["cmd.exe", "/c"]

compose := "docker compose -f ops/compose.yaml"

# List the commands. Running `just` with no argument lands here.
default:
    @just --list --unsorted

# First run after a clone: dependencies, local settings, and the commit hook.
setup:
    just _sync
    just _env
    -uv tool install --quiet pre-commit
    -pre-commit install
    @echo Ready. Next: just up, then just migrate, then just test.

[working-directory('backend')]
_sync:
    uv sync

# Copy .env.example to .env unless one already exists — never over a file that
# already has somebody's local secrets in it (Article 5-3).
[working-directory('backend')]
_env:
    uv run python -c "import pathlib, shutil; p = pathlib.Path('.env'); print('.env already present') if p.exists() else shutil.copy('.env.example', p)"

# `--wait` and not plain `up -d`: the latter returns long before the database
# accepts a connection, and a migration fired into that gap fails for no
# visible reason.

# Start PostgreSQL and Redis, and wait until they answer.
up:
    {{ compose }} up -d --wait

# Stop them. The data survives; `just nuke` is the one that does not.
down:
    {{ compose }} down

# Named separately from `down` because `down` must never be the command that
# loses a ledger somebody was in the middle of reading.

# Stop them and delete the local database volumes.
nuke:
    {{ compose }} down -v

# The whole suite. Extra arguments go to pytest:  just test -k reversal
[working-directory('backend')]
test *args:
    uv run pytest {{ args }}

# `lint-types` is deliberately not in this chain: the merge of phases
# 003/005/007 inherited 31 type errors in code that never ran mypy, so it
# reports rather than blocks. Run it directly — `just lint-types` — and put it
# back here the day it exits 0. See .github/workflows/ci.yml.
#
# Everything CI blocks on before it runs a single test, in the same order.
lint: lint-style lint-format lint-money lint-rules

[working-directory('backend')]
lint-style:
    uv run ruff check .

[working-directory('backend')]
lint-format:
    uv run ruff format --check .

# Reporting only for now — 31 known errors, none of them in apps/money.
[working-directory('backend')]
lint-types:
    uv run mypy .

# Article 3-2 — no binary floating point anywhere near money.
[working-directory('backend')]
lint-money:
    uv run python ../ops/checks/no_float_in_money.py

# One writer of auction state, one price on a vehicle, one builder of the
# vehicle card, one reader and writer of spreadsheets.
#
# Article 4-5 — one decision point each. Phase 005's four guards.
[working-directory('backend')]
lint-rules:
    uv run python ../ops/checks/auction_state_single_writer.py
    uv run python ../ops/checks/one_vehicle_price.py
    uv run python ../ops/checks/one_vehicle_card.py
    uv run python ../ops/checks/one_sheet_writer.py

# Rewrite what ruff can rewrite. CI never runs this — CI only ever checks.
fmt: _fix _format

[working-directory('backend')]
_fix:
    uv run ruff check --fix .

[working-directory('backend')]
_format:
    uv run ruff format .

# Apply migrations.
[working-directory('backend')]
migrate:
    uv run python manage.py migrate

# Write the migration a model change needs.
[working-directory('backend')]
makemigrations *args:
    uv run python manage.py makemigrations {{ args }}

# The same gate CI applies, so the drift is findable before the push.

# Fail if a model has drifted from its migrations.
[working-directory('backend')]
check-migrations:
    uv run python manage.py makemigrations --check --dry-run

# The development server.
[working-directory('backend')]
run port="8000":
    uv run python manage.py runserver {{ port }}

# Article 1-6: any number a customer can see must be traceable to entries, and
# this is what proves the cached balances still are.
#
# The management command itself arrives with T120 (phase 002); until then this
# recipe fails with Django's "Unknown command", which is the honest answer.

# Recompute the ledger from its entries and report every disagreement.
[working-directory('backend')]
verify:
    uv run python manage.py verify_ledger

# A shell on the database, whether it came from compose or a direct install.
[working-directory('backend')]
dbshell:
    uv run python manage.py dbshell

# Django's own system check.
[working-directory('backend')]
check:
    uv run python manage.py check

# Reports five warnings today; they disappear when T002's prod.py sets the
# SECURE_* settings. It fails only on errors, so it is a real gate now and a
# stricter one later.

# Django's deployment audit.
[working-directory('backend')]
check-deploy:
    uv run python manage.py check --deploy

# What CI runs, end to end, before you ask CI to run it.
ci: lint check-migrations test check-deploy
