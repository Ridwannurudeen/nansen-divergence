"""API v1 — webhook registration."""
import json
import secrets
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import AnyHttpUrl, BaseModel

router = APIRouter(prefix="/api/v1", tags=["v1"])


class WebhookRegister(BaseModel):
    url: AnyHttpUrl
    filters: dict = {}


@router.post("/webhooks/register", status_code=201)
def register_webhook(body: WebhookRegister):
    from nansen_divergence.history import DB_PATH, init_db

    wh_id = str(uuid.uuid4())
    secret = secrets.token_hex(32)
    now = datetime.now(timezone.utc).isoformat()

    conn = init_db(db_path=DB_PATH)
    conn.execute(
        "INSERT INTO webhooks (id, url, secret, filters, created_at) VALUES (?,?,?,?,?)",
        (wh_id, str(body.url), secret, json.dumps(body.filters), now),
    )
    conn.commit()
    conn.close()

    return {
        "id": wh_id,
        "secret": secret,
        "message": "Webhook registered. Verify payloads with X-Nansen-Signature header.",
    }


@router.delete("/webhooks/{webhook_id}", status_code=200)
def delete_webhook(webhook_id: str):
    from nansen_divergence.history import DB_PATH, init_db

    conn = init_db(db_path=DB_PATH)
    result = conn.execute("DELETE FROM webhooks WHERE id=?", (webhook_id,))
    conn.commit()
    conn.close()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return {"message": "Webhook deleted"}
