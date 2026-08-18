"""Backfill migration to encrypt existing plaintext OAuth tokens.

This script encrypts any existing plaintext GitHub/GitLab access tokens
in the users table. Run this after deploying the encryption migration.

Usage:
    python -m app.db.migrations.scripts.backfill_oauth_tokens

Or import and call:
    from app.db.migrations.scripts.backfill_oauth_tokens import backfill_tokens
    await backfill_tokens()
"""

import asyncio
import logging
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import encrypt_oauth_token, CURRENT_TOKEN_ENCRYPTION_VERSION
from app.db.session import async_session_factory
from app.models.user import User

logger = logging.getLogger(__name__)


async def backfill_tokens(db: AsyncSession | None = None) -> dict:
    """Encrypt all existing plaintext OAuth tokens.
    
    Args:
        db: Optional database session. If not provided, creates a new one.
        
    Returns:
        Dictionary with migration statistics.
    """
    stats = {
        "github_encrypted": 0,
        "gitlab_encrypted": 0,
        "errors": 0,
    }
    
    close_session = False
    if db is None:
        db = async_session_factory()
        close_session = True
    
    try:
        # Find users with plaintext GitHub tokens but no encrypted version
        result = await db.execute(
            select(User).where(
                User.github_access_token.isnot(None),
                User.github_access_token_encrypted.is_(None),
            )
        )
        github_users = result.scalars().all()
        
        for user in github_users:
            try:
                encrypted_token = encrypt_oauth_token(user.github_access_token)
                user.github_access_token_encrypted = encrypted_token
                user.token_encryption_version = CURRENT_TOKEN_ENCRYPTION_VERSION
                stats["github_encrypted"] += 1
                logger.info("Encrypted GitHub token", user_id=str(user.id))
            except Exception as exc:
                logger.error("Failed to encrypt GitHub token", user_id=str(user.id), error=str(exc))
                stats["errors"] += 1
        
        # Find users with plaintext GitLab tokens but no encrypted version
        result = await db.execute(
            select(User).where(
                User.gitlab_access_token.isnot(None),
                User.gitlab_access_token_encrypted.is_(None),
            )
        )
        gitlab_users = result.scalars().all()
        
        for user in gitlab_users:
            try:
                encrypted_token = encrypt_oauth_token(user.gitlab_access_token)
                user.gitlab_access_token_encrypted = encrypted_token
                user.token_encryption_version = CURRENT_TOKEN_ENCRYPTION_VERSION
                stats["gitlab_encrypted"] += 1
                logger.info("Encrypted GitLab token", user_id=str(user.id))
            except Exception as exc:
                logger.error("Failed to encrypt GitLab token", user_id=str(user.id), error=str(exc))
                stats["errors"] += 1
        
        await db.commit()
        logger.info("Backfill complete", stats=stats)
        
    except Exception as exc:
        await db.rollback()
        logger.error("Backfill failed", error=str(exc))
        raise
    finally:
        if close_session:
            await db.close()
    
    return stats


async def main():
    """Run the backfill script."""
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting OAuth token encryption backfill")
    stats = await backfill_tokens()
    logger.info("Backfill complete", stats=stats)


if __name__ == "__main__":
    asyncio.run(main())
