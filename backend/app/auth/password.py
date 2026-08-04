"""Password hashing and verification (bcrypt).

bcrypt is CPU-bound (~100-1100 ms on low-end hardware), so the blocking
primitives are only exposed through async wrappers that run on the thread pool.
This keeps the event loop responsive under concurrent authentication load.
"""

from __future__ import annotations

import asyncio

import bcrypt

_LOOP_BCRYPT_ROUNDS = 10


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=_LOOP_BCRYPT_ROUNDS)).decode("utf-8")


def _verify_password(plaintext: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(plaintext.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


async def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt (runs off the event loop)."""
    return await asyncio.to_thread(_hash_password, password)


async def verify_password(plaintext: str, password_hash: str) -> bool:
    """Verify a plaintext password against a bcrypt hash (off the event loop)."""
    return await asyncio.to_thread(_verify_password, plaintext, password_hash)
