import asyncio
import os
from sqlalchemy import text
from app.db.session import get_session_factory

async def check_data():
    try:
        session_factory = get_session_factory()
        async with session_factory() as session:
            # Raw SQL to check tables
            result = await session.execute(text("SELECT COUNT(*) FROM scans"))
            scan_count = result.scalar()
            print(f"✅ Total scans in database: {scan_count}")
            
            result = await session.execute(text("SELECT COUNT(*) FROM users"))
            user_count = result.scalar()
            print(f"✅ Total users: {user_count}")
            
            result = await session.execute(text("SELECT COUNT(*) FROM findings"))
            finding_count = result.scalar()
            print(f"✅ Total findings: {finding_count}")
            
            if scan_count > 0:
                result = await session.execute(
                    text("SELECT repository_url, status, overall_score FROM scans ORDER BY created_at DESC LIMIT 3")
                )
                scans = result.all()
                print(f"\n📊 Recent scans:")
                for scan in scans:
                    print(f"   - {scan[0]} | {scan[1]} | Score: {scan[2]}")
            
            if user_count > 0:
                result = await session.execute(
                    text("SELECT id, email, username FROM users LIMIT 3")
                )
                users = result.all()
                print(f"\n👥 Users:")
                for user in users:
                    print(f"   - {user[1]} | {user[2]}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(check_data())
