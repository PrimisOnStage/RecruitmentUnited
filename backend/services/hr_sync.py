"""Helpers for syncing candidates into BambooHR when hiring milestones are reached."""

import httpx
from fastapi import HTTPException

try:
    from backend.integrations.bamboohr import create_employee, employee_exists_by_email
except ImportError:
    import importlib

    bamboohr = importlib.import_module("integrations.bamboohr")
    create_employee = bamboohr.create_employee
    employee_exists_by_email = bamboohr.employee_exists_by_email


async def push_candidate_to_hrms(candidate: dict):
    """Push an internal candidate into BambooHR after defensive validation."""
    email = candidate.get("email")
    if not email:
        raise HTTPException(status_code=422, detail="Candidate email is required for HRMS sync")

    if candidate.get("source") == "bamboohr":
        raise HTTPException(status_code=409, detail="Candidate originated from BambooHR")

    try:
        if await employee_exists_by_email(email):
            raise HTTPException(status_code=409, detail="Employee already exists in BambooHR")
        return await create_employee(candidate)
    except HTTPException:
        raise
    except (ValueError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=502, detail=f"BambooHR sync failed: {exc}") from exc

