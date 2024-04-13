# routers/run_steps.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from utils.tranformers import db_to_pydantic_runstep
from lib.db import crud, schemas
from lib.db.database import get_db

router = APIRouter()


@router.get(
    "/threads/{thread_id}/runs/{run_id}/steps",
    response_model=schemas.SyncCursorPage[schemas.RunStep],
)
def get_run_steps(
    thread_id: str,
    run_id: str,
    limit: int = 20,
    order: str = "desc",
    after: str = None,
    before: str = None,
    db: Session = Depends(get_db),
):
    db_run_steps = crud.get_run_steps(
        db, thread_id, run_id, limit, order, after, before
    )

    run_steps = [db_to_pydantic_runstep(run_step) for run_step in db_run_steps]

    paginated_run_steps = schemas.SyncCursorPage(data=run_steps)

    return paginated_run_steps
