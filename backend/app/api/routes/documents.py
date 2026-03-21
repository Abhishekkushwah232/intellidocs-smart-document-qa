"""
Document routes: list, upload (storage + DB + ingestion), get, delete.

Enforces per-user isolation via `get_current_user` on every handler.
"""
from __future__ import annotations

import re
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.core.auth import CurrentUser, get_current_user
from app.core.config import settings
from app.core.db import ensure_pool_started, pool
from app.core.supabase import supabase_storage
from app.services.ingestion import ingest_document


router = APIRouter()


class DocumentOut(BaseModel):
    id: str
    filename: str
    status: str


class DocumentDetailOut(BaseModel):
    id: str
    filename: str
    status: str


def _sanitize_filename(name: str) -> str:
    name = name.strip()
    # Remove path separators and keep it simple.
    name = re.sub(r"[\\/]+", "_", name)
    return name[:200]


def _infer_doc_kind(filename: str, content_type: str | None) -> str:
    lower = filename.lower()
    if (content_type and "pdf" in content_type.lower()) or lower.endswith(".pdf"):
        return "pdf"
    if lower.endswith(".txt") or (content_type and "text" in content_type.lower()):
        return "text"
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF and TXT are supported.")


@router.post("/upload", response_model=list[DocumentOut])
async def upload_documents(
    files: list[UploadFile] = File(...),
    current_user: CurrentUser = Depends(get_current_user),
):
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No files provided.")

    ensure_pool_started()

    bucket = settings.supabase_storage_bucket
    created_docs: list[DocumentOut] = []

    # Supabase storage bucket names are case-sensitive in practice.
    # If your bucket is `Documents` but env says `documents`, normalize it.
    try:
        available_bucket_names = [b.name for b in supabase_storage.storage.list_buckets()]
        matched = next((n for n in available_bucket_names if n.lower() == bucket.lower()), None)
        if matched:
            bucket = matched
    except Exception:
        # If we can't list buckets, keep the configured value and let upload fail normally.
        pass

    # Ensure FK target exists: documents.user_id -> profiles.id
    # Supabase Auth creates users, but our `profiles` mirror table may not be auto-populated.
    try:
        user_uuid = uuid.UUID(current_user.user_id)
    except ValueError as e:
        raise HTTPException(status_code=401, detail="Invalid user_id in token") from e

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into profiles (id, email)
                values (%s, %s)
                on conflict (id) do update set email = excluded.email
                """,
                (str(user_uuid), current_user.email),
            )
            # Verify the FK target exists before inserting into `documents`.
            cur.execute("select 1 from profiles where id = %s", (str(user_uuid),))
            ok = cur.fetchone()
            if not ok:
                raise HTTPException(
                    status_code=500,
                    detail="profiles row still missing after upsert; check DB permissions/RLS",
                )
        conn.commit()

    for f in files:
        raw = await f.read()
        size_mb = len(raw) / (1024 * 1024)
        if size_mb > settings.max_upload_mb:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large: {f.filename} ({size_mb:.2f}MB). Max is {settings.max_upload_mb}MB.",
            )

        doc_kind = _infer_doc_kind(f.filename or "file", f.content_type)
        safe_name = _sanitize_filename(f.filename or "document")
        doc_id = uuid.uuid4()
        storage_path = f"{current_user.user_id}/{doc_id}/{safe_name}"

        # Create document row first.
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into documents (id, user_id, filename, storage_path, status, content)
                    values (%s, %s, %s, %s, %s, %s)
                    """,
                    (str(doc_id), current_user.user_id, safe_name, storage_path, "processing", ""),
                )
            conn.commit()

        # Upload to Supabase Storage (private bucket expected).
        try:
            supabase_storage.storage.from_(bucket).upload(
                storage_path,
                raw,
                {
                    "contentType": f.content_type or "application/octet-stream",
                },
            )
        except Exception as e:
            available = []
            try:
                available = [b.name for b in supabase_storage.storage.list_buckets()]
            except Exception:
                available = []
            # Best-effort rollback of document row.
            with pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("delete from documents where id = %s and user_id = %s", (str(doc_id), current_user.user_id))
                conn.commit()
            raise HTTPException(
                status_code=500,
                detail=f"Storage upload failed for bucket '{bucket}'. Error: {e}. Available buckets: {available}",
            )

        # Ingest immediately (safe limits in ingestion).
        try:
            ingest_document(
                user_id=current_user.user_id,
                document_id=doc_id,
                filename=safe_name,
                file_bytes=raw,
                content_type=f.content_type,
                doc_kind=doc_kind,
            )
        except Exception as e:
            with pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        update documents
                        set status = 'error'
                        where id = %s and user_id = %s
                        """,
                        (str(doc_id), current_user.user_id),
                    )
                conn.commit()
            raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")

        created_docs.append(DocumentOut(id=str(doc_id), filename=safe_name, status="ready"))

    return created_docs


@router.get("", response_model=list[DocumentOut])
def list_documents(current_user: CurrentUser = Depends(get_current_user)):
    ensure_pool_started()
    rows = []
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select id, filename, status
                from documents
                where user_id = %s
                order by uploaded_at desc
                """,
                (current_user.user_id,),
            )
            rows = cur.fetchall()

    return [DocumentOut(id=str(r[0]), filename=r[1], status=r[2]) for r in rows]


@router.get("/{document_id}", response_model=DocumentDetailOut)
def get_document(document_id: str, current_user: CurrentUser = Depends(get_current_user)):
    ensure_pool_started()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select id, filename, status
                from documents
                where id = %s and user_id = %s
                """,
                (document_id, current_user.user_id),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Document not found")

    return DocumentDetailOut(id=str(row[0]), filename=row[1], status=row[2])


@router.delete("/{document_id}")
def delete_document(document_id: str, current_user: CurrentUser = Depends(get_current_user)):
    ensure_pool_started()
    bucket = settings.supabase_storage_bucket

    storage_path: str | None = None
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select storage_path
                from documents
                where id = %s and user_id = %s
                """,
                (document_id, current_user.user_id),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Document not found")
            storage_path = row[0]

            # Deleting the document row should cascade-delete chunks due to FK.
            cur.execute(
                "delete from documents where id = %s and user_id = %s",
                (document_id, current_user.user_id),
            )
        conn.commit()

    # Best effort storage cleanup.
    try:
        # storage_delete expects a path relative to bucket root.
        supabase_storage.storage.from_(bucket).remove(storage_path)
    except Exception:
        # Storage cleanup failing shouldn't break DB correctness for the demo.
        pass

    return {"deleted": True, "id": document_id}

