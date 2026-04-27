"""
Create Stripe products and update database with price IDs.

This script:
1. Creates products in Stripe for each plan
2. Updates the database with the Stripe price IDs
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import select
from app.db.session import get_db
from app.models.payment import Plan
from app.config import settings


async def create_stripe_products():
    """Create Stripe products and update database."""
    import stripe as stripe_lib
    
    stripe_lib.api_key = settings.STRIPE_SECRET_KEY
    
    print("=" * 80)
    print("STRIPE PRODUCT CREATION")
    print("=" * 80)
    print()
    
    async for session in get_db():
        # Get all plans
        result = await session.execute(select(Plan).where(Plan.is_active == True))
        plans = result.scalars().all()
        
        print(f"Found {len(plans)} plans in database\n")
        
        for plan in plans:
            interval = plan.interval if isinstance(plan.interval, str) else plan.interval.value
            
            # Skip free plan
            if plan.price_usd == 0:
                print(f"⊘ Skipping free plan: {plan.display_name}")
                continue
            
            print(f"Processing: {plan.display_name} ({interval})")
            
            # Check if price ID already exists
            if interval == 'monthly' and plan.stripe_price_id_monthly:
                print(f"  ✓ Monthly price ID already exists: {plan.stripe_price_id_monthly}")
                continue
            
            if interval == 'yearly' and plan.stripe_price_id_yearly:
                print(f"  ✓ Yearly price ID already exists: {plan.stripe_price_id_yearly}")
                continue
            
            # Create product in Stripe
            try:
                product = stripe_lib.Product.create(
                    name=f"{plan.display_name} Plan",
                    description=plan.description or f"{plan.display_name} subscription plan",
                    metadata={
                        "plan_name": plan.name,
                        "interval": interval,
                    }
                )
                print(f"  ✓ Created Stripe product: {product.id}")
                
                # Determine currency
                currency = 'usd'
                
                # Create price in Stripe
                price = stripe_lib.Price.create(
                    product=product.id,
                    unit_amount=plan.price_usd,  # Already in cents
                    currency=currency,
                    recurring={
                        "interval": "month" if interval == "monthly" else "year"
                    },
                    metadata={
                        "plan_name": plan.name,
                        "interval": interval,
                    }
                )
                print(f"  ✓ Created Stripe price: {price.id} (${plan.price_usd/100}/mo)")
                
                # Update database
                if interval == 'monthly':
                    plan.stripe_price_id_monthly = price.id
                else:
                    plan.stripe_price_id_yearly = price.id
                
                await session.commit()
                print(f"  ✓ Updated database with price ID")
                
            except Exception as e:
                print(f"  ❌ Error: {e}")
                await session.rollback()
        
        print()
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        
        # Show final state
        result = await session.execute(select(Plan).where(Plan.is_active == True))
        plans = result.scalars().all()
        
        for plan in plans:
            interval = plan.interval if isinstance(plan.interval, str) else plan.interval.value
            price_id = plan.stripe_price_id_monthly if interval == 'monthly' else plan.stripe_price_id_yearly
            status = f"✓ {price_id}" if price_id else "❌ NOT SET"
            print(f"{plan.display_name:15} ({interval:10}) - {status}")
        
        break


if __name__ == "__main__":
    asyncio.run(create_stripe_products())
