import os
import httpx

BAMBOO_DOMAIN = os.getenv("BAMBOO_DOMAIN")
BAMBOO_API_KEY = os.getenv("BAMBOO_API_KEY")
ACCESS_TOKEN = os.getenv("BAMBOO_ACCESS_TOKEN")

BASE_URL = f"https://{BAMBOO_DOMAIN}.bamboohr.com/api/v1"


def _auth_and_headers() -> tuple[tuple[str, str] | None, dict]:
    headers = {"Accept": "application/json"}
    auth = None
    if ACCESS_TOKEN:
        headers["Authorization"] = f"Bearer {ACCESS_TOKEN}"
    elif BAMBOO_API_KEY:
        auth = (BAMBOO_API_KEY, "x")
    else:
        raise ValueError("Missing BambooHR credentials (BAMBOO_ACCESS_TOKEN or BAMBOO_API_KEY)")
    return auth, headers


def _split_name(full_name: str | None) -> tuple[str, str]:
    if not full_name:
        return "", ""
    parts = full_name.strip().split()
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def _candidate_to_employee_payload(candidate: dict) -> dict:
    first_name = candidate.get("first_name")
    last_name = candidate.get("last_name")

    if not first_name and not last_name:
        first_name, last_name = _split_name(candidate.get("name"))

    if not first_name:
        first_name = "Candidate"

    return {
        "firstName": first_name,
        "lastName": last_name or "",
        "jobTitle": candidate.get("current_role") or "",
        "workEmail": candidate.get("email"),
    }


async def get_employees_directory():
    url = f"{BASE_URL}/employees/directory"
    auth, headers = _auth_and_headers()

    async with httpx.AsyncClient(auth=auth, timeout=20.0) as client:
        res = await client.get(url, params={"fields": "id,firstName,lastName,workEmail,jobTitle,location,department"}, headers=headers)
        res.raise_for_status()

        return res.json()["employees"]


async def get_employee(employee_id):
    url = f"{BASE_URL}/employees/{employee_id}"
    auth, headers = _auth_and_headers()

    async with httpx.AsyncClient(auth=auth, timeout=20.0) as client:
        res = await client.get(url, params={"fields": "firstName,lastName,workEmail,jobTitle,location,department"}, headers=headers)
        res.raise_for_status()

        return res.json()

def convert_employee_to_candidate(emp):
    first = emp.get("firstName") or ""
    last = emp.get("lastName") or ""
    full_name = f"{first} {last}".strip() or None

    return {
        "name": full_name,
        "email": emp.get("workEmail"),
        "current_role": emp.get("jobTitle"),
        "location": emp.get("location"),
        "source": "bamboohr",
    }

async def sync_bamboo_candidates(upsert_function):
    employees = await get_employees_directory()

    for emp in employees:
        full = await get_employee(emp["id"])

        candidate = convert_employee_to_candidate(full)

        upsert_function(candidate)


async def employee_exists_by_email(email: str | None) -> bool:
    if not email:
        return False

    normalized = email.strip().lower()
    employees = await get_employees_directory()
    for employee in employees:
        work_email = (employee.get("workEmail") or "").strip().lower()
        if work_email == normalized:
            return True
    return False


async def create_employee(candidate):
    url = f"{BASE_URL}/employees"

    payload = _candidate_to_employee_payload(candidate)
    if not payload.get("workEmail"):
        raise ValueError("Candidate email is required to create BambooHR employee")

    auth, headers = _auth_and_headers()

    async with httpx.AsyncClient(timeout=20.0, auth=auth) as client:
        res = await client.post(url, json=payload, headers=headers)

    res.raise_for_status()
    if not res.content:
        return {"status": "created"}
    try:
        return res.json()
    except ValueError:
        return {"status": "created", "response_text": res.text}
