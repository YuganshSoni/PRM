from typing import Annotated

from fastapi import APIRouter, Depends

from server.core.dependencies import dependency_provider
from server.models.enums import UserRole
from server.models.user import User
from server.schemas.requests.config import UpdateSystemConfigRequest
from server.schemas.response_values import ConfigMessage
from server.schemas.responses.config import (
    SystemConfigResponse,
    SystemConfigUpdatedResponse,
)
from server.services.system_config_service import SystemConfigService


class ConfigRouter:
    def __init__(self) -> None:
        self.router = APIRouter(prefix="/config", tags=["config"])
        self.router.add_api_route(
            "",
            self.get_config,
            methods=["GET"],
            response_model=SystemConfigResponse,
        )
        self.router.add_api_route(
            "",
            self.update_config,
            methods=["PUT"],
            response_model=SystemConfigUpdatedResponse,
        )

    async def get_config(
        self,
        _admin: Annotated[User, Depends(dependency_provider.require_role(UserRole.ADMIN))],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        config_service: SystemConfigService = Depends(
            dependency_provider.get_system_config_service
        ),
    ) -> SystemConfigResponse:
        return await config_service.get_config()

    async def update_config(
        self,
        body: UpdateSystemConfigRequest,
        _admin: Annotated[User, Depends(dependency_provider.require_role(UserRole.ADMIN))],
        __: Annotated[User, Depends(dependency_provider.require_password_changed)],
        config_service: SystemConfigService = Depends(
            dependency_provider.get_system_config_service
        ),
    ) -> SystemConfigUpdatedResponse:
        await config_service.update_config(body)
        return SystemConfigUpdatedResponse(message=ConfigMessage.SETTINGS_UPDATED)
