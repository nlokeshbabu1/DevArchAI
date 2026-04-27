"""
Fix payment routing to prevent bypassing payment gateway.

This script provides two solutions:
1. IMMEDIATE FIX: Disable mock checkout mode - require real payment provider IDs
2. PERMANENT FIX: Guide to set up Stripe and Razorpay plan IDs
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import select, update, text
from app.db.session import get_db
from app.models.payment import Plan


async def fix_payment_routing():
    """Fix payment routing to prevent bypassing payment gateway."""
    
    print("=" * 80)
    print("PAYMENT ROUTING FIX")
    print("=" * 80)
    print()
    print("ROOT CAUSE:")
    print("  When stripe_price_id_monthly is None, payment_router.py returns a MOCK")
    print("  checkout URL that goes directly to /billing/success without payment!")
    print()
    print("This file explains two solutions:")
    print()
    print("=" * 80)
    print("SOLUTION 1: IMMEDIATE FIX (Disable Mock Mode)")
    print("=" * 80)
    print()
    print("Option A: Throw error when payment IDs are missing")
    print("  - Edit: backend/app/services/payment_router.py")
    print("  - Change: _create_stripe_session() method")
    print("  - Remove the mock fallback and raise ValueError instead")
    print()
    print("Option B: Redirect to pricing page with warning")
    print("  - Better UX: Tell user to configure payment provider first")
    print()
    print("I'll implement Option A (more secure):")
    print()
    
    choice = input("Apply immediate fix? (y/n): ").strip().lower()
    
    if choice == 'y':
        # Fix payment_router.py to disable mock mode
        payment_router_path = os.path.join(
            os.path.dirname(__file__),
            'app/services/payment_router.py'
        )
        
        print("\n📝 Updating payment_router.py to disable mock checkout...")
        
        with open(payment_router_path, 'r') as f:
            content = f.read()
        
        # Find and replace the mock fallback code
        old_code = '''        if not price_id:
            # Dev mode: return mock checkout URL when Stripe price IDs aren't configured
            session_id = f"dev_session_{plan.name}_{billing_interval}_{user.id}"
            return {
                "checkout_url": f"{frontend_url}/billing/success?session_id={session_id}&plan={plan.name}",
                "session_id": session_id,
                "provider": "stripe",
                "plan": plan.name,
                "billing_interval": billing_interval,
                "amount": amount,
                "currency": currency,
                "mock": True,
            }'''
        
        new_code = '''        if not price_id:
            # Payment provider not configured - block checkout
            raise ValueError(
                f"Stripe payment not configured for plan '{plan.name}' ({billing_interval}). "
                f"Please configure stripe_price_id_{billing_interval} in the plans table. "
                f"See: https://dashboard.stripe.com/products"
            )'''
        
        if old_code in content:
            content = content.replace(old_code, new_code)
            
            with open(payment_router_path, 'w') as f:
                f.write(content)
            
            print("✓ payment_router.py updated successfully!")
            print("\nNow Stripe checkout will fail with a clear error message if price IDs are missing.")
        else:
            print("⚠ Could not find the exact code to replace.")
            print("  Please manually edit backend/app/services/payment_router.py")
            print("  and remove the mock checkout fallback in _create_stripe_session()")
        
        print()
        print("=" * 80)
        print("SOLUTION 2: PERMANENT FIX (Configure Payment Providers)")
        print("=" * 80)
        print()
        print("Step 1: Create Products in Stripe")
        print("  1. Go to: https://dashboard.stripe.com/products")
        print("  2. Click 'Add product'")
        print("  3. Create products for: Plus, Pro, Enterprise")
        print("  4. Add recurring pricing (monthly and yearly)")
        print("  5. Copy the Price ID (starts with 'price_')")
        print()
        print("Step 2: Create Plans in Razorpay (for India)")
        print("  1. Go to: https://dashboard.razorpay.com/app/plans")
        print("  2. Click 'Create Plan'")
        print("  3. Create plans for: Plus, Pro, Enterprise")
        print("  4. Set billing frequency (monthly/yearly)")
        print("  5. Copy the Plan ID (starts with 'plan_')")
        print()
        print("Step 3: Update Database with Payment IDs")
        print("  Run this SQL to update the plans:")
        print()
        
        # Generate SQL update statements
        async for session in get_db():
            result = await session.execute(select(Plan).where(Plan.is_active == True))
            plans = result.scalars().all()
            
            print("  -- Update Stripe Price IDs")
            for plan in plans:
                interval = plan.interval if isinstance(plan.interval, str) else plan.interval.value
                print(f"  -- UPDATE plans SET stripe_price_id_{interval} = 'price_xxx' WHERE name = '{plan.name}' AND interval = '{interval}';")
            
            print()
            print("  -- Update Razorpay Plan IDs")
            for plan in plans:
                interval = plan.interval if isinstance(plan.interval, str) else plan.interval.value
                print(f"  -- UPDATE plans SET razorpay_plan_id_{interval} = 'plan_xxx' WHERE name = '{plan.name}' AND interval = '{interval}';")
            
            print()
            break
        
        print()
        print("=" * 80)
        print("NEXT STEPS:")
        print("=" * 80)
        print()
        print("1. ✓ Login flow fixed (already applied)")
        print("   - Users now go to checkout API after login")
        print("   - No longer bypass payment gateway")
        print()
        print("2. ✓ Mock checkout disabled (just applied)")
        print("   - Stripe checkout will fail with clear error if IDs missing")
        print("   - Prevents accidental free activations")
        print()
        print("3. ⏳ Configure payment providers (manual step)")
        print("   - Create products in Stripe/Razorpay dashboards")
        print("   - Update database with price IDs")
        print()
        print("4. ⏳ Test payment flow")
        print("   - Try upgrading to Plus plan")
        print("   - Verify redirect to Stripe/Razorpay payment page")
        print("   - Complete test payment")
        print("   - Verify subscription activates after payment")
        print()
        
    else:
        print("\nSkipping automatic fix.")
        print("Please manually edit backend/app/services/payment_router.py")
        print("and remove the mock checkout fallback.")


if __name__ == "__main__":
    asyncio.run(fix_payment_routing())
