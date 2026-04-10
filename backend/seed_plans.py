"""Seed script to populate plans table with Stripe and Razorpay IDs."""
import asyncio
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_db
from app.models.payment import Plan, PlanInterval


async def seed_plans():
    """Seed the plans table with initial data."""
    
    # Get a database session
    async for session in get_db():
        print("Checking if plans exist...")
        
        # Check if plans already exist
        result = await session.execute(select(Plan).where(Plan.is_active == True))
        existing_plans = result.scalars().all()
        
        if existing_plans:
            print(f"✓ Found {len(existing_plans)} existing plans in database")
            print("\nCurrent plans:")
            for plan in existing_plans:
                interval_str = plan.interval if isinstance(plan.interval, str) else plan.interval.value
                print(f"  - {plan.display_name} ({interval_str}) - ${plan.price_usd/100} USD")
            
            print("\n⚠ Plans already exist. Do you want to:")
            print("  1. Skip seeding (keep existing)")
            print("  2. Delete and recreate all plans")
            
            choice = input("\nEnter choice (1/2): ").strip()
            
            if choice == "1":
                print("Skipping seed...")
                return
            elif choice == "2":
                print("Deleting existing plans...")
                await session.execute(text("DELETE FROM plans"))
                await session.commit()
                print("✓ Existing plans deleted")
            else:
                print("Invalid choice. Skipping seed...")
                return
        
        print("\n🌱 Seeding plans...")
        
        # Define plans
        # Note: Prices are in cents/paise (smallest currency unit)
        # $9 USD = 900 cents, ₹999 INR = 99900 paise
        plans_data = [
            # FREE Plan
            {
                "name": "free",
                "display_name": "Free",
                "description": "Perfect for getting started",
                "interval": PlanInterval.MONTHLY,
                "price_usd": 0,
                "price_inr": 0,
                "price_eur": 0,
                "price_gbp": 0,
                "stripe_price_id_monthly": None,
                "stripe_price_id_yearly": None,
                "razorpay_plan_id_monthly": None,
                "razorpay_plan_id_yearly": None,
                "features": {
                    "scans_per_month": 3,
                    "repositories": 1,
                    "ai_suggestions": False,
                    "copy_fix": False,
                    "report_exports": False,
                    "github_automation": False,
                    "team_features": False,
                },
                "trial_days": 0,
                "sort_order": 1,
            },
            
            # PLUS Plan - Monthly (USD)
            {
                "name": "plus",
                "display_name": "Plus",
                "description": "For individual developers",
                "interval": PlanInterval.MONTHLY,
                "price_usd": 1200,  # $12.00
                "price_inr": 99900,  # ₹999
                "price_eur": 1100,  # €11.00
                "price_gbp": 1000,  # £10.00
                "stripe_price_id_monthly": None,  # TODO: Add from Stripe dashboard
                "stripe_price_id_yearly": None,  # TODO: Add from Stripe dashboard
                "razorpay_plan_id_monthly": None,  # TODO: Add from Razorpay dashboard
                "razorpay_plan_id_yearly": None,  # TODO: Add from Razorpay dashboard
                "features": {
                    "scans_per_month": 50,
                    "repositories": 5,
                    "ai_suggestions": True,
                    "copy_fix": True,
                    "report_exports": True,
                    "github_automation": False,
                    "team_features": False,
                },
                "trial_days": 14,
                "sort_order": 2,
            },
            
            # PLUS Plan - Yearly (USD)
            {
                "name": "plus",
                "display_name": "Plus",
                "description": "For individual developers",
                "interval": PlanInterval.YEARLY,
                "price_usd": 11520,  # $115.20/year (20% off = $9.60/month)
                "price_inr": 959040,  # ₹9,590/year
                "price_eur": 10560,  # €105.60/year
                "price_gbp": 9600,  # £96.00/year
                "stripe_price_id_monthly": None,
                "stripe_price_id_yearly": None,
                "razorpay_plan_id_monthly": None,
                "razorpay_plan_id_yearly": None,
                "features": {
                    "scans_per_month": 50,
                    "repositories": 5,
                    "ai_suggestions": True,
                    "copy_fix": True,
                    "report_exports": True,
                    "github_automation": False,
                    "team_features": False,
                },
                "trial_days": 14,
                "sort_order": 2,
            },
            
            # PRO Plan - Monthly (USD)
            {
                "name": "pro",
                "display_name": "Pro",
                "description": "For professional DevOps engineers",
                "interval": PlanInterval.MONTHLY,
                "price_usd": 2900,  # $29.00
                "price_inr": 249900,  # ₹2,499
                "price_eur": 2600,  # €26.00
                "price_gbp": 2400,  # £24.00
                "stripe_price_id_monthly": None,  # TODO: Add from Stripe dashboard
                "stripe_price_id_yearly": None,  # TODO: Add from Stripe dashboard
                "razorpay_plan_id_monthly": None,  # TODO: Add from Razorpay dashboard
                "razorpay_plan_id_yearly": None,  # TODO: Add from Razorpay dashboard
                "features": {
                    "scans_per_month": -1,  # Unlimited
                    "repositories": -1,  # Unlimited
                    "ai_suggestions": True,
                    "copy_fix": True,
                    "report_exports": True,
                    "github_automation": True,
                    "team_features": True,
                },
                "trial_days": 14,
                "sort_order": 3,
            },
            
            # PRO Plan - Yearly (USD)
            {
                "name": "pro",
                "display_name": "Pro",
                "description": "For professional DevOps engineers",
                "interval": PlanInterval.YEARLY,
                "price_usd": 27840,  # $278.40/year (20% off = $23.20/month)
                "price_inr": 2399040,  # ₹23,990/year
                "price_eur": 24960,  # €249.60/year
                "price_gbp": 23040,  # £230.40/year
                "stripe_price_id_monthly": None,
                "stripe_price_id_yearly": None,
                "razorpay_plan_id_monthly": None,
                "razorpay_plan_id_yearly": None,
                "features": {
                    "scans_per_month": -1,
                    "repositories": -1,
                    "ai_suggestions": True,
                    "copy_fix": True,
                    "report_exports": True,
                    "github_automation": True,
                    "team_features": True,
                },
                "trial_days": 14,
                "sort_order": 3,
            },
            
            # ENTERPRISE Plan - Monthly (USD)
            {
                "name": "enterprise",
                "display_name": "Enterprise",
                "description": "For companies and teams",
                "interval": PlanInterval.MONTHLY,
                "price_usd": 9900,  # $99.00
                "price_inr": 799900,  # ₹7,999
                "price_eur": 8900,  # €89.00
                "price_gbp": 7900,  # £79.00
                "stripe_price_id_monthly": None,  # TODO: Add from Stripe dashboard
                "stripe_price_id_yearly": None,  # TODO: Add from Stripe dashboard
                "razorpay_plan_id_monthly": None,  # TODO: Add from Razorpay dashboard
                "razorpay_plan_id_yearly": None,  # TODO: Add from Razorpay dashboard
                "features": {
                    "scans_per_month": -1,
                    "repositories": -1,
                    "ai_suggestions": True,
                    "copy_fix": True,
                    "report_exports": True,
                    "github_automation": True,
                    "team_features": True,
                    "compliance_reporting": True,
                    "custom_security_rules": True,
                    "dedicated_support": True,
                },
                "trial_days": 0,  # Contact sales
                "sort_order": 4,
            },
            
            # ENTERPRISE Plan - Yearly (USD)
            {
                "name": "enterprise",
                "display_name": "Enterprise",
                "description": "For companies and teams",
                "interval": PlanInterval.YEARLY,
                "price_usd": 95040,  # $950.40/year (20% off = $79.20/month)
                "price_inr": 7679040,  # ₹76,790/year
                "price_eur": 85440,  # €854.40/year
                "price_gbp": 75840,  # £758.40/year
                "stripe_price_id_monthly": None,
                "stripe_price_id_yearly": None,
                "razorpay_plan_id_monthly": None,
                "razorpay_plan_id_yearly": None,
                "features": {
                    "scans_per_month": -1,
                    "repositories": -1,
                    "ai_suggestions": True,
                    "copy_fix": True,
                    "report_exports": True,
                    "github_automation": True,
                    "team_features": True,
                    "compliance_reporting": True,
                    "custom_security_rules": True,
                    "dedicated_support": True,
                },
                "trial_days": 0,
                "sort_order": 4,
            },
        ]
        
        # Insert plans
        for plan_data in plans_data:
            plan = Plan(**plan_data)
            session.add(plan)
        
        await session.commit()
        
        print(f"✓ Successfully seeded {len(plans_data)} plans!")
        print("\nPlans created:")
        for plan_data in plans_data:
            print(f"  ✓ {plan_data['display_name']} ({plan_data['interval'].value})")
        
        print("\n⚠ IMPORTANT: You need to update the Stripe and Razorpay plan IDs!")
        print("  1. Create products in Stripe: https://dashboard.stripe.com/products")
        print("  2. Create plans in Razorpay: https://dashboard.razorpay.com/app/plans")
        print("  3. Update the stripe_price_id_* and razorpay_plan_id_* fields in the database")
        
        break


if __name__ == "__main__":
    asyncio.run(seed_plans())
