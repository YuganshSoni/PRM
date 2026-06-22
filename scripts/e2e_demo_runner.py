"""API-level end-to-end demo — run with server up after seed: alembic upgrade head && python -m server.seed.run_seed"""

from __future__ import annotations

import asyncio
import os
import sys
import time

import httpx


class E2eDemoRunner:
    def __init__(self, *, base_url: str, skip_ai: bool = False) -> None:
        self._base_url = base_url.rstrip("/")
        self._skip_ai = skip_ai
        self._token: str | None = None

    async def run(self) -> None:
        await self._wait_for_server()
        async with httpx.AsyncClient(base_url=self._base_url, timeout=30.0) as client:
            self._client = client
            await self._step("Admin login", self._admin_login)
            await self._step("Admin list users", self._admin_list_users)
            if not self._skip_ai:
                await self._step("Admin view config", self._admin_view_config)
            await self._step("Health check", self._health_check)
        print("\nE2E demo completed successfully.")

    async def _wait_for_server(self, *, attempts: int = 15, delay_seconds: float = 1.0) -> None:
        async with httpx.AsyncClient(base_url=self._base_url, timeout=5.0) as client:
            for attempt in range(1, attempts + 1):
                try:
                    response = await client.get("/health")
                    if response.status_code == 200:
                        return
                except httpx.HTTPError:
                    pass
                if attempt < attempts:
                    time.sleep(delay_seconds)
        raise RuntimeError(
            f"Server not ready at {self._base_url}. "
            "Start with: uvicorn server.main:app --port 8000 (after DB seed)."
        )

    async def _step(self, label: str, coro) -> None:
        print(f"→ {label}...")
        await coro()
        print(f"  ✓ {label}")

    async def _admin_login(self) -> None:
        response = await self._client.post(
            "/auth/login",
            json={"username": "admin", "password": "Admin@1234"},
        )
        response.raise_for_status()
        self._token = response.json()["access_token"]

    async def _admin_list_users(self) -> None:
        response = await self._client.get(
            "/users",
            headers=self._headers(),
        )
        response.raise_for_status()

    async def _admin_view_config(self) -> None:
        response = await self._client.get("/config", headers=self._headers())
        response.raise_for_status()

    async def _health_check(self) -> None:
        response = await self._client.get("/health")
        response.raise_for_status()
        db = await self._client.get("/health/db")
        db.raise_for_status()

    def _headers(self) -> dict[str, str]:
        if self._token is None:
            raise RuntimeError("Not authenticated")
        return {"Authorization": f"Bearer {self._token}"}


def main() -> None:
    base_url = os.environ.get("API_BASE_URL", "http://localhost:8000")
    skip_ai = os.environ.get("PRM_SKIP_AI", "").lower() in ("1", "true", "yes")
    try:
        asyncio.run(E2eDemoRunner(base_url=base_url, skip_ai=skip_ai).run())
    except (httpx.HTTPError, RuntimeError) as exc:
        print(f"E2E demo failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
