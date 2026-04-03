"""
Database seeding script using Faker.
Run with `nikame db seed`.
"""
import asyncio
import logging
import json
import os
from faker import Faker
from core.database import AsyncSessionLocal
from sqlalchemy import text

# Add your models here
# from api.auth.models import User

logger = logging.getLogger(__name__)
fake = Faker()

async def seed_data():
    """Seed the database with initial data."""
    async with AsyncSessionLocal() as session:
        logger.info("Starting database seeding...")
        
        # Example: Seed Users
        # for _ in range(10):
        #     user = User(
        #         email=fake.unique.email(),
        #         username=fake.unique.user_name(),
        #         password_hash="argon2_placeholder_hash", # Replace with real hash
        #         is_active=True
        #     )
        #     session.add(user)
        
        # Example: Raw SQL seed
        # await session.execute(text("INSERT INTO ..."))
        
        await session.commit()
        logger.info("Successfully seeded database.")

if __name__ == "__main__":
    # Configure basic logging for the script
    logging.basicConfig(level=logging.INFO)
    asyncio.run(seed_data())
