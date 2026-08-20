from __future__ import annotations

import asyncio
from time import perf_counter

from trans_flow.agent import TranslationAgent
from trans_flow.callback_client import TranslationCallbackClient
from trans_flow.models import (
    TranslationCallback,
    TranslationResultStatus,
)
from trans_flow.queue import TranslationJob


class TranslationAgentError(RuntimeError):
    pass


class TranslationRejectedError(RuntimeError):
    pass


class TranslationWorker:
    def __init__(
        self,
        *,
        agent: TranslationAgent,
        callback_client: TranslationCallbackClient,
        timeout_seconds: float,
    ) -> None:
        self._agent = agent
        self._callback = callback_client
        self._timeout = timeout_seconds

    async def __call__(self, job: TranslationJob) -> None:
        started = perf_counter()
        try:
            async with asyncio.timeout(self._timeout):
                raw_response = await self._agent.translate(job.command)
        except Exception as error:
            elapsed = int((perf_counter() - started) * 1000)
            await self._callback.send(
                job.command,
                TranslationCallback(
                    requestId=job.command.request_id,
                    sourceHash=job.command.source_hash,
                    status=TranslationResultStatus.FAILED,
                    model=self._agent.model_name,
                    elapsedMilliseconds=elapsed,
                    error=f"{type(error).__name__}: {error}"[:2000],
                ),
            )
            # Let the queue remove its completed-command fingerprint. A user
            # can restart the FAILED process and submit this same SQL fragment
            # again after the model dependency has recovered.
            raise TranslationAgentError("Agent translation failed") from error

        elapsed = int((perf_counter() - started) * 1000)
        accepted = await self._callback.send(
            job.command,
            TranslationCallback(
                requestId=job.command.request_id,
                sourceHash=job.command.source_hash,
                status=TranslationResultStatus.COMPLETED,
                rawResponse=raw_response,
                model=self._agent.model_name,
                elapsedMilliseconds=elapsed,
            ),
        )
        if not accepted:
            # Validation is owned by trans-api. A rejected candidate puts the
            # process into FAILED and must remain retryable after user restart.
            raise TranslationRejectedError("trans-api rejected the translation")
