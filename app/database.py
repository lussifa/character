"""Legacy database compatibility module.

The runtime described by the README is file-based. Older imports may still
expect a `get_db` symbol, so this module keeps a tiny no-op dependency provider
without requiring SQLAlchemy or creating SQLite files.
"""


def get_db():
    yield None
