from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_db
from ..models import User, Agent
from ..ingress.auth import get_current_user

router = APIRouter(prefix="/api/agents", tags=["agents"])

# Pydantic models
class AgentCreate(BaseModel):
    name: str
    prompt: str

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    prompt: Optional[str] = None

class AgentResponse(BaseModel):
    id: int
    user_id: str
    name: str
    prompt: str
    created_at: str

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj: Agent):
        return cls(
            id=obj.id,
            user_id=obj.user_id,
            name=obj.name,
            prompt=obj.prompt,
            created_at=obj.created_at.isoformat()
        )

# Routes

@router.get("/", response_model=List[AgentResponse])
async def list_agents(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Agent).where(Agent.user_id == user.user_id)
    result = await db.execute(stmt)
    agents = result.scalars().all()
    return [AgentResponse.from_orm(agent) for agent in agents]

@router.post("/", response_model=AgentResponse)
async def create_agent(
    agent_in: AgentCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    new_agent = Agent(
        user_id=user.user_id,
        name=agent_in.name,
        prompt=agent_in.prompt
    )
    db.add(new_agent)
    await db.commit()
    await db.refresh(new_agent)
    return AgentResponse.from_orm(new_agent)

@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: int,
    agent_update: AgentUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Agent).where(Agent.id == agent_id, Agent.user_id == user.user_id)
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
        
    if agent_update.name is not None:
        agent.name = agent_update.name
    if agent_update.prompt is not None:
        agent.prompt = agent_update.prompt
        
    await db.commit()
    await db.refresh(agent)
    return AgentResponse.from_orm(agent)

@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Agent).where(Agent.id == agent_id, Agent.user_id == user.user_id)
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
        
    await db.delete(agent)
    await db.commit()
    return None

def build_agents_router() -> APIRouter:
    return router
