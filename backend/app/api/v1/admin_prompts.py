from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import require_admin
from app.database.models.prompt import Prompt, PromptVersion
from app.database.models.user import User
from app.database.session import get_db
from app.schemas.prompt import PromptActivateVersion, PromptCreate, PromptResponse, PromptUpdate, PromptVersionResponse

PROMPT_LOAD_OPTS = [selectinload(Prompt.versions)]

router = APIRouter(prefix="/admin/prompts", tags=["admin-prompts"])


@router.post("", response_model=PromptResponse, status_code=status.HTTP_201_CREATED)
async def create_prompt(
    prompt_data: PromptCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    existing = await db.scalar(select(Prompt).where(Prompt.name == prompt_data.name))
    if existing:
        raise HTTPException(status_code=400, detail="Prompt name already exists")

    prompt = Prompt(
        name=prompt_data.name,
        category=prompt_data.category,
        current_version=1,
        is_active=prompt_data.is_active,
    )
    db.add(prompt)
    await db.flush()

    version = PromptVersion(
        prompt_id=prompt.id,
        version=1,
        content=prompt_data.content,
        changelog="Initial version",
        is_active=True,
        created_by=current_user.id,
    )
    db.add(version)

    await db.commit()
    await db.refresh(prompt, ["versions"])
    return prompt


@router.get("", response_model=List[PromptResponse])
async def list_prompts(
    category: Optional[str] = None,
    include_versions: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    query = select(Prompt).options(*PROMPT_LOAD_OPTS)
    if category:
        query = query.where(Prompt.category == category)
    query = query.order_by(Prompt.name)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{prompt_id}", response_model=PromptResponse)
async def get_prompt(
    prompt_id: str,
    include_versions: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    query = select(Prompt).where(Prompt.id == prompt_id)
    if include_versions:
        query = query.options(selectinload(Prompt.versions))
    prompt = await db.scalar(query)

    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt


@router.get("/by-name/{name}", response_model=PromptResponse)
async def get_prompt_by_name(
    name: str,
    version: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    prompt = await db.scalar(select(Prompt).where(Prompt.name == name).options(selectinload(Prompt.versions)))
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    if version is not None:
        ver = next((v for v in prompt.versions if v.version == version), None)
        if not ver:
            raise HTTPException(status_code=404, detail=f"Version {version} not found")

    return prompt


@router.patch("/{prompt_id}", response_model=PromptResponse)
async def update_prompt(
    prompt_id: str,
    prompt_data: PromptUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    prompt = await db.scalar(select(Prompt).where(Prompt.id == prompt_id))
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    if prompt_data.category is not None:
        prompt.category = prompt_data.category
    if prompt_data.is_active is not None:
        prompt.is_active = prompt_data.is_active

    if prompt_data.content is not None:
        prompt.current_version += 1
        new_version = PromptVersion(
            prompt_id=prompt.id,
            version=prompt.current_version,
            content=prompt_data.content,
            changelog=prompt_data.changelog or f"Updated to version {prompt.current_version}",
            is_active=True,
            created_by=current_user.id,
        )
        await db.execute(
            PromptVersion.__table__.update().where(PromptVersion.prompt_id == prompt.id).values(is_active=False)
        )
        db.add(new_version)

    await db.commit()
    await db.refresh(prompt, ["versions"])
    return prompt


@router.post("/{prompt_id}/versions", response_model=PromptVersionResponse, status_code=status.HTTP_201_CREATED)
async def create_prompt_version(
    prompt_id: str,
    content: str,
    changelog: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    prompt = await db.scalar(select(Prompt).where(Prompt.id == prompt_id))
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    prompt.current_version += 1
    await db.execute(
        PromptVersion.__table__.update().where(PromptVersion.prompt_id == prompt.id).values(is_active=False)
    )

    version = PromptVersion(
        prompt_id=prompt.id,
        version=prompt.current_version,
        content=content,
        changelog=changelog or f"Version {prompt.current_version}",
        is_active=True,
        created_by=current_user.id,
    )
    db.add(version)
    await db.commit()
    await db.refresh(version)
    return version


@router.post("/{prompt_id}/activate", response_model=PromptVersionResponse)
async def activate_prompt_version(
    prompt_id: str,
    data: PromptActivateVersion,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    prompt = await db.scalar(select(Prompt).where(Prompt.id == prompt_id))
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    version = await db.scalar(
        select(PromptVersion).where(PromptVersion.prompt_id == prompt_id, PromptVersion.version == data.version)
    )
    if not version:
        raise HTTPException(status_code=404, detail=f"Version {data.version} not found")

    await db.execute(
        PromptVersion.__table__.update().where(PromptVersion.prompt_id == prompt_id).values(is_active=False)
    )
    version.is_active = True
    prompt.current_version = data.version

    await db.commit()
    await db.refresh(version)
    return version


@router.delete("/{prompt_id}/versions/{version}")
async def delete_prompt_version(
    prompt_id: str,
    version: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    ver = await db.scalar(
        select(PromptVersion).where(PromptVersion.prompt_id == prompt_id, PromptVersion.version == version)
    )
    if not ver:
        raise HTTPException(status_code=404, detail="Version not found")

    if ver.is_active:
        raise HTTPException(status_code=400, detail="Cannot delete active version")

    await db.delete(ver)
    await db.commit()
    return {"message": "Version deleted"}


@router.get("/{prompt_id}/versions", response_model=List[PromptVersionResponse])
async def list_prompt_versions(
    prompt_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    versions = await db.scalars(
        select(PromptVersion).where(PromptVersion.prompt_id == prompt_id).order_by(desc(PromptVersion.version))
    )
    return versions.all()
