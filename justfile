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
    uv run python ../ops/checks/one_upload_gate.py
    uv run python ../ops/checks/every_capability_guards_something.py

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

# Rebuild the committed OpenAPI schema (T621).
#
# Run this after changing a serializer, a view or a route. The file it writes is
# the contract two generated clients are built from — the Flutter app and the
# web — so the diff it produces is the API change itself, in a form a reviewer
# can read. CI fails when the committed copy and the code disagree.
schema:
    cd backend && uv run python manage.py spectacular --validate --fail-on-warn --file openapi/schema.yaml
    @echo "backend/openapi/schema.yaml updated — commit the diff"


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

# ---------------------------------------------------------------------------
# ويب العميل — الفيز 011.
#
# `npm ci` and not `npm install` everywhere here for the same reason CI uses it:
# the lockfile is the input, and a command that may resolve a different tree
# than the lockfile describes is a command that eventually explains a failure
# nobody can reproduce.
# ---------------------------------------------------------------------------

# Install the web's dependencies exactly as the lockfile has them.
[working-directory('web')]
web-install:
    npm ci

# The development server, on http://localhost:3000.
[working-directory('web')]
web:
    npm run dev

# Regenerate the typed client from the committed schema.
#
# Run it after `just schema`. The two are separate steps deliberately: the
# backend's schema is the contract and the client is derived from it, so
# regenerating the client can never be what changes the contract.
[working-directory('web')]
web-schema:
    npm run schema

# Everything the web is held to, in the order CI runs it.
[working-directory('web')]
web-check:
    npm run schema:check
    npm run typecheck
    npm run lint
    npm test
    npm run build

# The web's constitutional guards. Node, not Python, and run from the repo root
# because each of them walks `web/` from there.
web-lint-rules:
    node ops/checks/web_tokens_are_httponly.mjs
    node ops/checks/web_one_vehicle_card.mjs
    node ops/checks/web_money_is_never_computed.mjs
    node ops/checks/web_no_eligibility_logic.mjs
    node ops/checks/web_uses_the_contract_only.mjs

# What CI runs, end to end, before you ask CI to run it.
ci: lint check-migrations test check-deploy web-lint-rules web-check
