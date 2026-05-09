from fastapi import APIRouter, Depends, Request

from .orchestrator import Orchestrator
from .schemas import ServiceListResponse, ServiceNotFoundError, StatusResponse, SuccessResponse
from .state import ServiceStatus

router = APIRouter()


def get_orchestrator(request: Request):
    return request.app.state.orchestrator


@router.get("/services", response_model=ServiceListResponse)
def get_services(orchestrator: Orchestrator = Depends(get_orchestrator)) -> ServiceListResponse:
    services = orchestrator.list_services()
    return ServiceListResponse(content=services)


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
        return StatusResponse(content=str(e), status="404")
    except Exception as e:
        return StatusResponse(content=str(e), status="500")


@router.post("/services/{name}/start")
async def start_service(
    name: str, orchestrator: Orchestrator = Depends(get_orchestrator)
) -> ServiceStatus:
    try:
        await orchestrator.start(name)
        return SuccessResponse(content=f"sucess: {name} is starting", status=200)
    except ServiceNotFoundError as e:
        return StatusResponse(content=str(e), status="404")
    except Exception as e:
        return StatusResponse(content=str(e), status="500")


@router.post("/services/{name}/stop")
async def stop_service(
    name: str, orchestrator: Orchestrator = Depends(get_orchestrator)
) -> ServiceStatus:
    try:
        await orchestrator.stop(name)
        return SuccessResponse(content=f"sucess: {name} is stopping", status=200)
    except ServiceNotFoundError as e:
        return StatusResponse(content=str(e), status="404")
    except Exception as e:
        return StatusResponse(content=str(e), status="500")
