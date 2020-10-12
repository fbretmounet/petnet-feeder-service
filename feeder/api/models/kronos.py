from typing import List, Optional

from pydantic import BaseModel

from feeder import settings


class NewGateway(BaseModel):
    """
    This is the structure of a new feeder registering itself.
    Example: {
        "name":"SF Gateway",
        "uid":"smartfeeder-795ae773737d",
        "osName":"FreeRTOS",
        "type":"Local",
        "softwareName":"SMART FEEDER",
        "softwareVersion":"2.8.0",
        "sdkVersion":"1.3.12"
    }
    """

    name: str
    uid: str
    osName: str
    type: str
    softwareName: str
    softwareVersion: str
    sdkVersion: str


class Gateway(NewGateway):
    hid: str
    pri: str
    applicationHid: str = settings.app_id
    discoveredAt: int = 0

    class Config:
        orm_mode = True


class BasePaginatedList(BaseModel):
    size: int = 0
    page: int = 0
    totalSize: int = 0
    totalPages: int = 1


class PaginatedGatewayList(BasePaginatedList):
    data: List[Gateway] = []


class AddGatewayResponse(BaseModel):
    hid: str
    message: str
    links: Optional[dict]
    pri: Optional[str]


class NewDevice(BaseModel):
    """
    Example: {
        'name': 'SF20A',
        'type': 'SMART FEEDER',
        'uid': 'smartfeeder-4b09fa082bbd-prod',
        'gatewayHid': 'd48d71fb4478ed189b37699ac1ea665fbed5a577',
        'softwareName': 'SMART FEEDER',
        'softwareVersion': '2.8.0'
    }
    """
    name: str
    type: str
    uid: str
    gatewayHid: str
    softwareName: str
    softwareVersion: str


class Device(NewDevice):
    hid: str
    discoveredAt: int = 0
    lastPingedAt: int = 0

    class Config:
        orm_mode = True


class PaginatedDeviceList(BasePaginatedList):
    data: List[Device] = []


class GatewayConfiguration(BaseModel):
    cloudPlatform: str
    key: dict
