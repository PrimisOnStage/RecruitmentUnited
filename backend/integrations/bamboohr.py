import os
import httpx

BAMBOO_DOMAIN = os.getenv("BAMBOO_DOMAIN")
BAMBOO_API_KEY = os.getenv("BAMBOO_API_KEY")

BASE_URL = f"https://{BAMBOO_DOMAIN}.bamboohr.com/api/v1"


async def get_employees_directory():
    url = f"{BASE_URL}/employees/directory"

    async with httpx.AsyncClient(auth=(BAMBOO_API_KEY, "x")) as client:
        res = await client.get(url, params={"fields": "id,firstName,lastName,workEmail,jobTitle,location,department"}, headers={"Accept": "application/json"})
        res.raise_for_status()

        return res.json()["employees"]

async def get_employee(employee_id):
    url = f"{BASE_URL}/employees/{employee_id}"

    async with httpx.AsyncClient(auth=(BAMBOO_API_KEY, "x")) as client:
        res = await client.get(url, params={"fields": "firstName,lastName,workEmail,jobTitle,location,department"}, headers={"Accept": "application/json"})
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
