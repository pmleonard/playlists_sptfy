# Contributing

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
make setup-dev
make bootstrap
```

`make` targets auto-prepend `.venv/bin` to `PATH` when `.venv` exists.
Use `.venv/bin/python` as your project interpreter so dependency checks (including `pyproject.toml` inspections) resolve against the same environment.

This initializes:

- `data/settings/settings.json` from `data/settings/default_settings.json`
- `data/settings/config.json` from `data/settings/default_config.json`
- `data/song_lists/songs.json` from `data/song_lists/songs.template.json`

If you want to reset all three files to defaults/template:

```bash
make bootstrap-force
```

## Daily workflow

Run local CI checks before opening a PR:

```bash
make ci-local
```

Useful individual commands:

```bash
make validate-config
make test
make lint
make precommit
make run
```

## Settings and config files

- `data/settings/settings.json` stores runtime flags (`dry_run`, `strict_mode`, logging, HTTP retry knobs).
- `data/settings/config.json` stores file paths and `tags_filter`.

The app normalizes and backfills both files during startup.

## Pull request checklist

- [ ] Add or update tests for behavior changes.
- [ ] Run `make validate-config` and ensure it passes.
- [ ] Run `make ci-local` and ensure it passes.
- [ ] Keep output format changes intentional (CSV, playlist txt, duplicate markdown).
- [ ] Update docs when changing settings/config keys, Make targets, or outputs.
- [ ] Keep patches focused; split unrelated changes into separate PRs.
