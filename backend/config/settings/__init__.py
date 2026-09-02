"""Environment-specific settings.

Pick one with `DJANGO_SETTINGS_MODULE`:

    config.settings.dev    local development (the default)
    config.settings.test   CI and local test runs — inherits `prod`
    config.settings.prod   production

Importing this package does not configure Django; `base` is not an
environment and must never be pointed at directly.
"""
