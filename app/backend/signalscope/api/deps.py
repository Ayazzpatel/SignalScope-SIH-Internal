from typing import Annotated

from fastapi import Depends, Request

from signalscope.core.config import Settings, get_settings
from signalscope.services.detector import Detector


def get_detector(request: Request) -> Detector:
    return request.app.state.detector


SettingsDep = Annotated[Settings, Depends(get_settings)]
DetectorDep = Annotated[Detector, Depends(get_detector)]
