.PHONY: bootstrap bootstrap-force setup-dev validate-config ci-local test run lint precommit

# Prefer project-local tooling for make targets when a local virtualenv exists.
ifneq (,$(wildcard .venv/bin))
export PATH := $(abspath .venv/bin):$(PATH)
endif

bootstrap:
	@if [ ! -f data/settings/settings.json ] && [ -f data/settings/default_settings.json ]; then \
		cp data/settings/default_settings.json data/settings/settings.json; \
		echo "Created data/settings/settings.json from default_settings.json"; \
	fi
	@if [ ! -f data/settings/config.json ] && [ -f data/settings/default_config.json ]; then \
		cp data/settings/default_config.json data/settings/config.json; \
		echo "Created data/settings/config.json from default_config.json"; \
	fi
	@if [ ! -f data/song_lists/songs.json ] && [ -f data/song_lists/songs.template.json ]; then \
		cp data/song_lists/songs.template.json data/song_lists/songs.json; \
		echo "Created data/song_lists/songs.json from songs.template.json"; \
	fi

bootstrap-force:
	@if [ -f data/settings/default_settings.json ]; then \
		cp data/settings/default_settings.json data/settings/settings.json; \
		echo "Overwrote data/settings/settings.json from default_settings.json"; \
	fi
	@if [ -f data/settings/default_config.json ]; then \
		cp data/settings/default_config.json data/settings/config.json; \
		echo "Overwrote data/settings/config.json from default_config.json"; \
	fi
	@if [ -f data/song_lists/songs.template.json ]; then \
		cp data/song_lists/songs.template.json data/song_lists/songs.json; \
		echo "Overwrote data/song_lists/songs.json from songs.template.json"; \
	fi

setup-dev:
	python -m pip install -e .
	python -m pip install 'pre-commit>=3.7' 'pytest>=8.0' 'ruff>=0.5'
	pre-commit install

validate-config:
	python -m playlists_sptfy --validate-config


ci-local: precommit validate-config lint test

test:
	pytest -q

run:
	python -m playlists_sptfy

lint:
	ruff check src tests

precommit:
	pre-commit run --all-files

