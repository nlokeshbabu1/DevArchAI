"""Quick diagnostic to check payment setup."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import select
from app.db.session import get_db
from app.models.payment import Plan


async def check_payment_setup():
    """Check current payment setup."""
    async for session in get_db():
        print("=" * 80)
        print("PAYMENT SETUP DIAGNOSTIC")
        print("=" * 80)
        
        # Check plans
        result = await session.execute(select(Plan).where(Plan.is_active == True))
        plans = result.scalars().all()
        
        print(f"\n✓ Found {len(plans)} plans in database\n")
        
        for plan in plans:
            interval_str = plan.interval if isinstance(plan.interval, str) else plan.interval.value
            print(f"Plan: {plan.display_name} ({interval_str})")
            print(f"  Price: ${plan.price_usd/100} USD | ₹{plan.price_inr/100} INR")
            print(f"  Stripe Price ID (monthly): {plan.stripe_price_id_monthly or '❌ NOT SET'}")
            print(f"  Stripe Price ID (yearly): {plan.stripe_price_id_yearly or '❌ NOT SET'}")
            print(f"  Razorpay Plan ID (monthly): {plan.razorpay_plan_id_monthly or '❌ NOT SET'}")
            print(f"  Razorpay Plan ID (yearly): {plan.razorpay_plan_id_yearly or '❌ NOT SET'}")
            print()
        
        print("=" * 80)
        print("DIAGNOSIS:")
        print("=" * 80)
        
        # Check if Stripe/Razorpay IDs are set
        has_stripe_ids = any(p.stripe_price_id_monthly for p in plans)
        has_razorpay_ids = any(p.razorpay_plan_id_monthly for p in plans)
        
        if not has_stripe_ids and not has_razorpay_ids:
            print("\n❌ ISSUE FOUND: Payment provider plan IDs are NOT configured!")
            print("\nThis is why users bypass payment gateway.")
            print("\nThe code in payment_router.py has a fallback for Stripe:")
            print("  - If stripe_price_id is None, it returns a MOCK checkout URL")
            print("  - This mock URL goes directly to /billing/success without payment!")
            print("\nSOLUTION:")
            print("  1. Create products in Stripe Dashboard: https://dashboard.stripe.com/products")
            print("  2. Copy the price IDs (price_xxx)")
            print("  3. Create plans in Razorpay Dashboard: https://dashboard.razorpay.com/app/plans")
            print("  4. Copy the plan IDs (plan_xxx)")
            print("  5. Update the database with these IDs")
            print("\nQuick fix for testing:")
            print("  Run: python fix_payment_routing.py")
        else:
            print("\n✓ Payment provider IDs are configured")
            if not has_stripe_ids:
                print("⚠ Stripe IDs missing - will fallback to mock for non-India users")
            if not has_razorpay_ids:
                print("⚠ Razorpay IDs missing - India users will see errors")
        
        print()
        break


if __name__ == "__main__":
    asyncio.run(check_payment_setup())
