import asyncpg

from config import settings

class Psql:
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    async def create_pool():
        pool = await asyncpg.create_pool(f"{settings['pg']['uri']}/tubadata", max_size=85)
        return pool