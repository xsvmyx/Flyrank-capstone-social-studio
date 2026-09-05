from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from services.llm_service import GroqService

router = APIRouter(prefix="/ai", tags=["AI Generation"])


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=5, description="Input text or prompt for generation")
    system_instruction: str | None = Field(
        default="You are an expert social media manager.",
        description="Optional system instruction for the LLM"
    )

class GenerateResponse(BaseModel):
    generated_text: str
    status: str = "success"


@router.post("/generate", response_model=GenerateResponse, status_code=status.HTTP_200_OK)
async def generate_text(payload: GenerateRequest):
    """
    Direct endpoint to generate content using Groq LLM API.
    """
    try:
        output = await GroqService.generate_completion(
            prompt=payload.prompt,
            system_instruction=payload.system_instruction
        )
        return GenerateResponse(generated_text=output)
    except RuntimeError as err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(err)
        )