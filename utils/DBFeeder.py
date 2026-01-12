"""Compatibility wrapper for feeding demo data in tests."""

from src.DBFeeder import backupDB, get_demodata, initDB

__all__ = ["get_demodata", "initDB", "backupDB"]

