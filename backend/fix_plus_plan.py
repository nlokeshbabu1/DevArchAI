"""Fix Plus plan monthly Stripe price ID."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import stripe as stripe_lib
from app.db.session import get_db
from app.models.payment import Plan
from app.config import settings
from sqlalchemy import select


async def fix_plus_plan():
    stripe_lib.api_key = settings.STRIPE_SECRET_KEY
    
    async for session in get_db():
        result = await session.execute(
            select(Plan).where(Plan.name == 'plus', Plan.interval == 'monthly')
        )
        plus_plan = result.scalar_one_or_none()
        
        if plus_plan:
            print(f'Fixing Plus plan monthly price ID...')
            print(f'Current value: {plus_plan.stripe_price_id_monthly}')
            
            # Create product
            product = stripe_lib.Product.create(
                name='Plus Plan',
                description='For individual developers',
                metadata={'plan_name': 'plus', 'interval': 'monthly'}
            )
            
            # Create price ($12.00 = 1200 cents)
            price = stripe_lib.Price.create(
                product=product.id,
                unit_amount=1200,  # $12.00
                currency='usd',
                recurring={'interval': 'month'},
                metadata={'plan_name': 'plus', 'interval': 'monthly'}
            )
            
            plus_plan.stripe_price_id_monthly = price.id
            await session.commit()
            
            print(f'✓ Updated Plus plan monthly price ID: {price.id}')
        
        break


if __name__ == "__main__":
    asyncio.run(fix_plus_plan())
