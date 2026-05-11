from fastapi import APIRouter, Depends, HTTPException, Request

from .logging import get_logger
from .orchestrator import Orchestrator
from .schemas import ServiceListResponse, ServiceNotFoundError, StatusResponse, SuccessResponse

router = APIRouter()
logger = get_logger(__name__)


def get_orchestrator(request: Request) -> Orchestrator:
    return request.app.state.orchestrator


@router.get("/services", response_model=ServiceListResponse)
def get_services(orchestrator: Orchestrator = Depends(get_orchestrator)) -> ServiceListResponse:
    services = orchestrator.list_services()
    return ServiceListResponse(content=services)


@router.get("/services/{name}/activity", response_model=StatusResponse)
def get_service_status(
    name: str, orchestrator: Orchestrator = Depends(get_orchestrator)
) -> StatusResponse:
    # orchestrator.update_last_activity(name)
    seconds = orchestrator.get_seconds_until_sleep(name)
    return StatusResponse(
        content=str(seconds),
        status=200
    )


@router.get("/services/{name}/status", response_model=StatusResponse)
def get_service_status(
    name: str, orchestrator: Orchestrator = Depends(get_orchestrator)
) -> StatusResponse:
    try:
        status = orchestrator.get_status(name)
        return StatusResponse(
            content=status,
            status=200,
        )
    except ServiceNotFoundError as e:
        logger.error(f"get_service_status | service not found name={name}, exception={e}")
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error(f"get_service_status | internal server error name={name}, exception={e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/services/{name}/start")
async def start_service(
    name: str, orchestrator: Orchestrator = Depends(get_orchestrator)
) -> SuccessResponse:
    try:
        await orchestrator.start(name)
        return SuccessResponse(content=f"sucess: {name} is starting", status=200)
    except ServiceNotFoundError as e:
        logger.error(f"start_service | service not found name={name}, exception={e}")
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error(f"start_service | internal server error name={name}, exception={e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/services/{name}/stop")
async def stop_service(
    name: str, orchestrator: Orchestrator = Depends(get_orchestrator)
) -> SuccessResponse:
    try:
        await orchestrator.stop(name)
        return SuccessResponse(content=f"sucess: {name} is stopping", status=200)
    except ServiceNotFoundError as e:
        logger.error(f"stop_service | service not found name={name}, exception={e}")
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error(f"stop_service | internal server error name={name}, exception={e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
