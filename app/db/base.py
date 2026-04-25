"""
Shared SQLAlchemy declarative base.

This module exists to support a clean project structure:
`app/db/base.py` and `app/db/session.py`.
"""
from app.db.database import Base

__all__ = ["Base"]
