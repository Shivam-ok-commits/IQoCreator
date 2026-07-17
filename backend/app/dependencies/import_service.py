from __future__ import annotations

from app.services.import_service import ImportService


_import_service: ImportService | None = None


def get_import_service() -> ImportService:
    global _import_service
    if _import_service is None:
        _import_service = ImportService()
    return _import_service
