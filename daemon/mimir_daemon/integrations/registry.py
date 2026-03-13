"""Registro de integraciones de timesheet."""

import logging

from .base import TimesheetClient

logger = logging.getLogger(__name__)


class IntegrationRegistry:
    """Registro central de integraciones."""

    def __init__(self) -> None:
        self._timesheet_client: TimesheetClient | None = None

    def set_timesheet_client(self, client: TimesheetClient) -> None:
        self._timesheet_client = client
        logger.info("Cliente de timesheet registrado: %s", type(client).__name__)

    @property
    def timesheet(self) -> TimesheetClient | None:
        return self._timesheet_client
