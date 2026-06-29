from fastapi import APIRouter, Header, HTTPException, Query, Request

from app.services.rag import rag_store


router = APIRouter(
    prefix="/rag",
    tags=["rag"],
)


@router.post("/upload")
async def upload_file(
    request: Request,
    filename: str | None = Query(default=None),
    x_filename: str | None = Header(default=None, alias="X-Filename"),
):
    raw_content = await request.body()
    if not raw_content:
        raise HTTPException(status_code=400, detail="uploaded file is empty")

    safe_filename = (filename or x_filename or "uploaded.txt").strip()
    if not safe_filename:
        safe_filename = "uploaded.txt"

    try:
        text = raw_content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail="only utf-8 text files are supported for now",
        ) from exc

    try:
        return rag_store.add_document(safe_filename, text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
