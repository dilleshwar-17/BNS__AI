"""Case intelligence router (Phase 18). Matches plan contract:
/cases, /cases/{id}/facts, /cases/{id}/evidence, /cases/{id}/analysis,
/cases/{id}/timeline, /cases/{id}/contradictions.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import audit_service
from app.auth.dependencies import get_current_user
from app.core.request_id import get_request_id
from app.db.session import get_db
from app.models.case import (
    CandidateProvision,
    CaseContradiction,
    CaseEvidence,
)
from app.models.user import User
from app.schemas.case import (
    AnalysisSummary,
    CaseCreate,
    CaseDetail,
    CaseList,
    CaseMemberCreate,
    CaseRead,
    ContradictionList,
    ContradictionRead,
    EvidenceList,
    EvidenceRead,
    FactCreate,
    FactList,
    FactRead,
    MemberRead,
    PartyCreate,
    PartyRead,
    ProvisionRead,
    TimelineCreate,
    TimelineList,
    TimelineRead,
)
from app.services.case import CaseService

router = APIRouter()
service = CaseService()


@router.post("", response_model=CaseRead, status_code=201, summary="Create a case")
async def create_case(
    payload: CaseCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    case = await service.create_case(
        session,
        user_id=current_user.id,
        title=payload.title,
        description=payload.description,
        matter_number=payload.matter_number,
        court=payload.court,
    )
    await audit_service.record(
        session,
        action="cases.create",
        request_id=get_request_id(),
        user_id=current_user.id,
        resource_type="case",
        resource_id=str(case.id),
    )
    await session.commit()
    await session.refresh(case)
    return CaseRead.model_validate(case)


@router.get("", response_model=CaseList, summary="List my cases")
async def list_cases(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CaseList:
    cases = await service.list_cases(session, current_user.id, limit=limit, offset=offset)
    total = await service.count_cases(session, current_user.id)
    return CaseList(cases=[CaseRead.model_validate(c) for c in cases], total=total)


@router.get("/{case_id}", response_model=CaseDetail, summary="Get a case detail")
async def get_case(
    case_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CaseDetail:
    case = await service.get_case(session, case_id, current_user.id)
    return CaseDetail(
        **CaseRead.model_validate(case).model_dump(),
        members=[MemberRead.model_validate(m) for m in await service.list_members(session, case.id)],
        parties=[PartyRead.model_validate(p) for p in await service.list_parties(session, case.id)],
        facts=[FactRead.model_validate(f) for f in await service.list_facts(session, case.id)],
    )


@router.post("/{case_id}/members", response_model=MemberRead, summary="Add a case member")
async def add_member(
    case_id: int,
    payload: CaseMemberCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> MemberRead:
    case = await service.get_case(session, case_id, current_user.id)
    member = await service.add_member(
        session, case_id=case.id, user_id=payload.user_id, role_in_case=payload.role_in_case
    )
    await session.commit()
    await session.refresh(member)
    return MemberRead.model_validate(member)


@router.post("/{case_id}/parties", response_model=PartyRead, summary="Add a party")
async def add_party(
    case_id: int,
    payload: PartyCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PartyRead:
    case = await service.get_case(session, case_id, current_user.id)
    party = await service.add_party(
        session, case_id=case.id, name=payload.name, side=payload.side, is_claimant=payload.is_claimant
    )
    await session.commit()
    await session.refresh(party)
    return PartyRead.model_validate(party)


@router.post("/{case_id}/facts", response_model=FactRead, summary="Add a fact")
async def add_fact(
    case_id: int,
    payload: FactCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> FactRead:
    case = await service.get_case(session, case_id, current_user.id)
    fact = await service.add_fact(
        session, case_id=case.id, text=payload.text, provenance=payload.provenance, confidence=payload.confidence
    )
    await session.commit()
    await session.refresh(fact)
    return FactRead.model_validate(fact)


@router.get("/{case_id}/facts", response_model=FactList, summary="List facts")
async def list_facts(
    case_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> FactList:
    case = await service.get_case(session, case_id, current_user.id)
    facts = await service.list_facts(session, case.id)
    return FactList(facts=[FactRead.model_validate(f) for f in facts])


@router.post("/{case_id}/timeline", response_model=TimelineRead, summary="Add timeline event")
async def add_timeline(
    case_id: int,
    payload: TimelineCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TimelineRead:
    case = await service.get_case(session, case_id, current_user.id)
    event = await service.add_timeline_event(
        session, case_id=case.id, when=payload.when, description=payload.description
    )
    await session.commit()
    await session.refresh(event)
    return TimelineRead.model_validate(event)


@router.get("/{case_id}/timeline", response_model=TimelineList, summary="List timeline")
async def list_timeline(
    case_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TimelineList:
    case = await service.get_case(session, case_id, current_user.id)
    events = await service.list_timeline(session, case.id)
    return TimelineList(events=[TimelineRead.model_validate(e) for e in events])


@router.get("/{case_id}/evidence", response_model=EvidenceList, summary="List evidence")
async def list_evidence(
    case_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> EvidenceList:
    case = await service.get_case(session, case_id, current_user.id)
    rows = list((await session.execute(select(CaseEvidence).where(CaseEvidence.case_id == case.id))).scalars().all())
    return EvidenceList(items=[EvidenceRead.model_validate(e) for e in rows])


@router.get("/{case_id}/contradictions", response_model=ContradictionList, summary="List contradictions")
async def list_contradictions(
    case_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ContradictionList:
    case = await service.get_case(session, case_id, current_user.id)
    rows = list(
        (await session.execute(select(CaseContradiction).where(CaseContradiction.case_id == case.id))).scalars().all()
    )
    return ContradictionList(items=[ContradictionRead.model_validate(c) for c in rows])


@router.get("/{case_id}/analysis", response_model=AnalysisSummary, summary="Analysis summary (candidate provisions)")
async def analysis(
    case_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AnalysisSummary:
    case = await service.get_case(session, case_id, current_user.id)
    provisions = list(
        (await session.execute(select(CandidateProvision).where(CandidateProvision.case_id == case.id))).scalars().all()
    )
    return AnalysisSummary(provisions=[ProvisionRead.model_validate(p) for p in provisions])
