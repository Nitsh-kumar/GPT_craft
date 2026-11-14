from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import User
from app.api.routes.chat import get_current_user
from app.services.memory import MemoryService
from app.schemas.memory import (
    UserPreferencesUpdate,
    UserPreferencesResponse,
    UserMemoryCreate,
    UserMemoryResponse,
    MemoryListResponse,
)

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("/preferences", response_model=UserPreferencesResponse)
def get_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve the current user's custom instructions and personalization settings"""
    prefs = MemoryService.get_preferences(db, current_user.id)
    return prefs


@router.put("/preferences", response_model=UserPreferencesResponse)
def update_preferences(
    body: UserPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update custom instructions and toggle memory on/off"""
    prefs = MemoryService.update_preferences(
        db=db,
        user_id=current_user.id,
        profile=body.custom_instructions_profile,
        style=body.custom_instructions_style,
        memory_enabled=body.memory_enabled,
    )
    return prefs


@router.get("", response_model=MemoryListResponse)
def list_memories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all active remembered facts and context for the user"""
    prefs = MemoryService.get_preferences(db, current_user.id)
    memories = MemoryService.list_memories(db, current_user.id)
    return MemoryListResponse(
        memories=memories,
        total=len(memories),
        memory_enabled=prefs.memory_enabled,
    )


@router.post("", response_model=UserMemoryResponse, status_code=status.HTTP_201_CREATED)
def add_memory(
    body: UserMemoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manually add a memory item to the user's persistent store"""
    if not body.content.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Memory content cannot be empty",
        )
    return MemoryService.add_memory(
        db=db,
        user_id=current_user.id,
        content=body.content,
        category=body.category or "general",
    )


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_memory(
    memory_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a specific memory belonging to the current user"""
    deleted = MemoryService.delete_memory(db, current_user.id, memory_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory not found",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("", status_code=status.HTTP_200_OK)
def clear_all_memories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Clear all memories for the current user"""
    count = MemoryService.clear_all(db, current_user.id)
    return {"message": "All memories cleared successfully", "count": count}
