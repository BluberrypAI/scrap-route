from functools import partial
from hmac import compare_digest
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, field_validator

from resource_ai.agents.facility_discovery import (
    FacilityDiscoveryRequest,
    FacilityDiscoveryResponse,
    discover,
)
from resource_ai.agents.intake_review import (
    IntakeAgentRequest,
    IntakeAgentResponse,
    IntakeBatchRequest,
    IntakeBatchResponse,
    review_batch,
    review_candidate,
)
from resource_ai.agents.lot_review import LotContext, LotPhoto, PhotoObservation, observe_photos
from resource_ai.agents.review_config import review_config
from resource_ai.core.config import Settings, get_settings
from resource_ai.integrations.llm_client import review_with_azure

router = APIRouter(prefix="/treatment", tags=["treatment"])
bearer = HTTPBearer(auto_error=False)


def internal_settings(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]):
    settings = get_settings()
    token = settings.scrap_intake_service_token.get_secret_value()
    if (
        not token
        or not credentials
        or not compare_digest(credentials.credentials.encode(), token.encode())
    ):
        raise HTTPException(status_code=401, detail="Service authentication required")
    return settings


InternalSettings = Annotated[Settings, Depends(internal_settings)]


@router.post("/intake-review", response_model=IntakeAgentResponse)
def intake_review(request: IntakeAgentRequest, settings: InternalSettings):
    return review_candidate(request, partial(review_with_azure, settings))


@router.post("/intake-reviews", response_model=IntakeBatchResponse)
def intake_reviews(request: IntakeBatchRequest, settings: InternalSettings):
    if request.photo_observations is not None and (
        request.observation_signature != review_config(settings)["photo_signature"]
    ):
        raise HTTPException(status_code=409, detail="Observation version changed")
    return review_batch(request, partial(review_with_azure, settings))


class PhotoObservationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    photos: list[LotPhoto] = Field(min_length=1, max_length=4)

    @field_validator("photos")
    @classmethod
    def unique_photos(cls, photos):
        if len({photo.photo_id for photo in photos}) != len(photos):
            raise ValueError("Duplicate photo IDs")
        return photos


class PhotoObservationResponse(BaseModel):
    status: str
    observations: list[PhotoObservation] = Field(default_factory=list)
    signature: str


@router.get("/review-config")
def intake_review_config(settings: InternalSettings):
    return review_config(settings)


@router.post("/photo-observations", response_model=PhotoObservationResponse)
def photo_observations(request: PhotoObservationRequest, settings: InternalSettings):
    context = LotContext(
        state_key="photo-observation",
        mass_kg=1,
        condition="Independent photograph observation.",
        photos=request.photos,
    )
    rows = observe_photos(context, partial(review_with_azure, settings))
    return PhotoObservationResponse(
        status="reviewed" if rows is not None else "model_unavailable",
        observations=rows or [],
        signature=review_config(settings)["photo_signature"],
    )


@router.post("/facility-web-search", response_model=FacilityDiscoveryResponse)
def facility_web_search(request: FacilityDiscoveryRequest, settings: InternalSettings):
    return discover(request, settings)
