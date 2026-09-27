from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.gemini_service import gemini_service

router = APIRouter()


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    result = await gemini_service.generate_response(
        message=request.message,
        language=request.language,
        crop=request.crop,
        quantity=request.quantity,
        farmer_lat=request.latitude,
        farmer_lon=request.longitude,
        db=db,
    )

    return ChatResponse(
        answer=result["answer"],
        language=result["language"],
        intent=result["intent"],
        context_used=result["context_used"],
        data_status=result["data_status"],
        source=result["source"],
        error_code=result.get("error_code"),
        error_message=result.get("error_message"),
    )
