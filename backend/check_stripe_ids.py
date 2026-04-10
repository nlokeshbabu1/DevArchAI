"""Quick check of Stripe price IDs in database."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import select
from app.db.session import get_db
from app.models.payment import Plan


async def check_stripe_ids():
    async for session in get_db():
        result = await session.execute(
            select(Plan).where(Plan.is_active == True)
        )
        plans = result.scalars().all()
        
        print("Plan Name | Interval | Price USD | Stripe Price ID")
        print("-" * 80)
        for plan in plans:
            interval = plan.interval if isinstance(plan.interval, str) else plan.interval.value
            price_id = plan.stripe_price_id_monthly if interval == 'monthly' else plan.stripe_price_id_yearly
            print(f"{plan.name:12} | {interval:10} | ${plan.price_usd/100:8.2f} | {price_id or '❌ NOT SET'}")
        
        break


if __name__ == "__main__":
    asyncio.run(check_stripe_ids())
