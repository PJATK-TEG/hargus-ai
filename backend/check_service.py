import asyncio
from hargus_api.db.base import AsyncSessionLocal
from hargus_api.services.candidate_service import list_vacancies

async def main():
    async with AsyncSessionLocal() as session:
        v = await list_vacancies(session)
        print("Vacancies:", v)

asyncio.run(main())
