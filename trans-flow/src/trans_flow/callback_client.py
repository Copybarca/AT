from __future__ import annotations

import asyncio

import httpx

from trans_flow.models import TranslationCallback, TranslationCommand


class TranslationCallbackClient:
    def __init__(
        self,
        *,
        base_url: str,
        service_token: str,
        retries: int,
        retry_delay_seconds: float,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = service_token
        self._retries = retries
        self._retry_delay = retry_delay_seconds
        self._client = client or httpx.AsyncClient()
        self._owns_client = client is None

    async def send(
        self,
        command: TranslationCommand,
        callback: TranslationCallback,
    ) -> bool:
        url = self._base_url + command.callback_path
        last_error: Exception | None = None
        for attempt in range(self._retries):
            try:
                response = await self._client.post(
                    url,
                    headers={"Authorization": f"Bearer {self._token}"},
                    json=callback.model_dump(by_alias=True, exclude_none=True),
                )
                response.raise_for_status()
                payload = response.json()
                return isinstance(payload, dict) and payload.get("accepted") is True
            except (httpx.HTTPError, OSError) as error:
                last_error = error
                if attempt + 1 < self._retries:
                    await asyncio.sleep(self._retry_delay)
        raise RuntimeError("Could not deliver translation callback") from last_error

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()
