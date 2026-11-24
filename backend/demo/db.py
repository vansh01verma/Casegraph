"""Dedicated engine/session for Demo Mode. Deliberately separate from the live
application's engine."""
from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from . import config
from .models import DemoBase

_engine = None
_Session = None


def get_engine():
    global _engine, _Session
    if _engine is None:
        config.ensure_dirs()
        kwargs = {"connect_args": {"check_same_thread": False}} if config.DEMO_DATABASE_URL.startswith("sqlite") else {}
        _engine = create_engine(config.DEMO_DATABASE_URL, future=True, **kwargs)
        _Session = sessionmaker(bind=_engine, expire_on_commit=False, future=True)
        DemoBase.metadata.create_all(_engine)
    return _engine


def reset_engine() -> None:
    """Used by tests to point at a fresh database."""
    global _engine, _Session
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _Session = None


@contextmanager
def demo_session():
    get_engine()
    s = _Session()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()
