from __future__ import annotations

import hmac
from contextlib import asynccontextmanager
from hashlib import sha256
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException, status

from trans_flow.agent import OllamaTranslationAgent, TranslationAgent
from trans_flow.callback_client import TranslationCallbackClient
from trans_flow.models import TranslationCommand
from trans_flow.queue import SubmitOutcome, TranslationJob, TranslationTaskQueue
from trans_flow.settings import ServiceSettings
from trans_flow.worker import TranslationWorker


def create_app(
    settings: ServiceSettings | None = None,
    *,
    queue: TranslationTaskQueue | None = None,
    agent: TranslationAgent | None = None,
) -> FastAPI:
    configured = settings or ServiceSettings()
    callback: TranslationCallbackClient | None = None
    owned_agent: TranslationAgent | None = None
    if queue is None:
        owned_agent = agent or OllamaTranslationAgent(
            host=configured.ollama_host,
            model=configured.ollama_model,
        )
        callback = TranslationCallbackClient(
            base_url=configured.trans_api_base_url,
            service_token=configured.service_token,
            retries=configured.translation_callback_retries,
            retry_delay_seconds=configured.translation_callback_retry_delay_seconds,
        )
        queue = TranslationTaskQueue(
            capacity=configured.translation_queue_capacity,
            worker_count=configured.translation_worker_count,
            handler=TranslationWorker(
                agent=owned_agent,
                callback_client=callback,
                timeout_seconds=configured.translation_timeout_seconds,
            ),
        )
    task_queue = queue

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await task_queue.start()
        try:
            yield
        finally:
            await task_queue.stop()
            if callback is not None:
                await callback.close()
            if owned_agent is not None:
                await owned_agent.close()

    app = FastAPI(title="Translation Agent Flow", lifespan=lifespan)

    def require_token(authorization: str | None) -> None:
        expected = f"Bearer {configured.service_token}"
        if authorization is None or not hmac.compare_digest(authorization, expected):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "UP"}

    @app.post("/internal/v1/translations", status_code=status.HTTP_202_ACCEPTED)
    async def submit_translation(
        command: TranslationCommand,
        authorization: Annotated[str | None, Header()] = None,
        idempotency_key: Annotated[str | None, Header()] = None,
    ) -> dict[str, str | int | bool]:
        require_token(authorization)
        expected_key = f"translation-{command.process_id}-{command.segment_id}"
        if idempotency_key != expected_key:
            raise HTTPException(status_code=400, detail="Invalid Idempotency-Key")
        fingerprint = sha256(
            command.model_dump_json(by_alias=True).encode("utf-8")
        ).hexdigest()
        outcome = task_queue.submit(
            TranslationJob(command=command, fingerprint=fingerprint)
        )
        if outcome is SubmitOutcome.CONFLICT:
            raise HTTPException(status_code=409, detail="Conflicting translation command")
        if outcome is SubmitOutcome.FULL:
            raise HTTPException(status_code=429, detail="Translation queue is full")
        return {
            "requestId": command.request_id,
            "processId": command.process_id,
            "segmentId": command.segment_id,
            "accepted": True,
        }

    return app
