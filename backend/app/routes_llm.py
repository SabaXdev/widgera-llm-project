import json
from typing import Any, Dict
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from openai import OpenAI
from . import auth, models, schemas, storage
from .config import settings
from .database import get_db

router = APIRouter(prefix="/api", tags=["llm"])

@router.post("/upload-image", response_model=schemas.ImageUploadResponse)
async def upload_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    data = await file.read()
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file upload"
        )

    content_hash = storage.hash_bytes(data)

    # Deduplicate per user by content hash
    existing = (
        db.query(models.Image)
        .filter(
            models.Image.user_id == current_user.id,
            models.Image.content_hash == content_hash,
        )
        .first()
    )
    if existing:
        return schemas.ImageUploadResponse(
            image_id=existing.id,
            object_key=existing.object_key,
            mime_type=existing.mime_type,
        )

    object_key, _ = storage.upload_image_bytes(data, file.content_type)

    image = models.Image(
        user_id=current_user.id,
        object_key=object_key,
        mime_type=file.content_type,
        content_hash=content_hash,
    )
    db.add(image)
    db.commit()
    db.refresh(image)

    return schemas.ImageUploadResponse(
        image_id=image.id, object_key=image.object_key, mime_type=image.mime_type
    )


def build_json_schema(fields: list[schemas.FieldDefinition]) -> Dict[str, Any]:
    properties: Dict[str, Any] = {}
    required: list[str] = []
    for f in fields:
        if f.type == "string":
            properties[f.name] = {"type": "string"}
        elif f.type == "number":
            properties[f.name] = {"type": "number"}
        else:
            raise ValueError(f"Unsupported field type: {f.type}")
        required.append(f.name)
    return {
        "type": "object", 
        "properties": properties, 
        "required": required, 
        "additionalProperties": False,
    }


def get_or_create_cache(
    db: Session,
    prompt: str,
    fields: list[schemas.FieldDefinition],
    image_hash: str | None,
) -> tuple[Dict[str, Any] | None, models.QueryCache | None]:
    key_payload = {
        "prompt": prompt,
        "fields": [f.model_dump() for f in fields],
        "image_hash": image_hash,
    }
    cache_key = storage.hash_bytes(json.dumps(key_payload, sort_keys=True).encode("utf-8"))

    cached = (
        db.query(models.QueryCache)
        .filter(models.QueryCache.cache_key == cache_key)
        .first()
    )
    if cached:
        return json.loads(cached.response_json), cached

    return None, models.QueryCache(
        cache_key=cache_key,
        prompt=prompt,
        field_schema_json=json.dumps(key_payload["fields"]),
        image_hash=image_hash,
        response_json="",  # filled later
    )


@router.post(
    "/structured-query", response_model=schemas.StructuredQueryResponse, status_code=200
)
async def structured_query(
    payload: schemas.StructuredQueryRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    image_bytes: bytes | None = None
    image_hash: str | None = None

    if payload.image_id is not None:
        image = db.get(models.Image, payload.image_id)
        if image is None or image.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Image not found"
            )
        image_bytes = storage.get_image_bytes(image.object_key)
        image_hash = image.content_hash

    cached_result, cache_row = get_or_create_cache(
        db, payload.prompt, payload.fields, image_hash
    )
    if cached_result is not None:
        return schemas.StructuredQueryResponse(result=cached_result, cached=True)

    # Call OpenAI for structured JSON output
    client = OpenAI(api_key=settings.openai_api_key)

    json_schema = build_json_schema(payload.fields)

    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": "You are a helpful assistant that returns ONLY JSON following the provided JSON schema. Do not include any additional commentary.",
        }
    ]

    user_content: list[dict[str, Any]] = [{"type": "text", "text": payload.prompt}]
    if image_bytes is not None:
        import base64

        b64 = base64.b64encode(image_bytes).decode("ascii")
        user_content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
            }
        )

    messages.append({"role": "user", "content": user_content})

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "structured_output",
                "schema": json_schema,
                "strict": True,
            },
        },
    )

    if not completion.choices:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No response from language model",
        )

    raw_message_content = completion.choices[0].message.content
    if not raw_message_content:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Empty response from language model",
        )

    try:
        if isinstance(raw_message_content, str):
            raw_content_text = raw_message_content
        elif isinstance(raw_message_content, list):
            # OpenAI python SDK may return list of content parts
            text_parts = [
                part.get("text", "")
                for part in raw_message_content
                if isinstance(part, dict) and part.get("type") == "text"
            ]
            raw_content_text = "".join(text_parts)
        else:
            raw_content_text = str(raw_message_content)

        result_json = json.loads(raw_content_text)
    except json.JSONDecodeError:
        # Best effort: wrap as string result
        result_json = {"raw": raw_message_content}

    if cache_row is not None:
        cache_row.response_json = json.dumps(result_json)
        db.add(cache_row)
        db.commit()

    return schemas.StructuredQueryResponse(result=result_json, cached=False)
