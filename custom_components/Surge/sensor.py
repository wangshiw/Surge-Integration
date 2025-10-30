from typing import Dict
import logging
from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.const import UnitOfDataVolume

from .surge_api import SurgeAPIClient
from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

class SurgeTrafficSensor(SensorEntity):
    def __init__(self, api: SurgeAPIClient, update_interval: int):
        self._api = api
        self._update_interval = update_interval
        self._traffic_data = {"upload": 0.0, "download": 0.0, "total": 0.0}
        self._attr_unique_id = f"{DOMAIN}_traffic_sensor"
        self._attr_name = "Surge Total Traffic"
        self._attr_unit_of_measurement = UnitOfDataVolume.MEGABYTES
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{self._api._host}:{self._api._port}")},
            name="Surge Controller",
            model="Surge Mac/iOS",
            manufacturer="Surge"
        )

        # 初始化数据更新协调器
        self._coordinator = DataUpdateCoordinator(
            self.hass,
            _LOGGER,
            name=self._attr_name,
            update_method=self._async_update_data,
            update_interval=self._update_interval,
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        await self._coordinator.async_config_entry_first_refresh()

    async def _async_update_data(self) -> None:
        """从 API 刷新流量数据"""
        try:
            self._traffic_data = await self._api.get_traffic()
        except Exception as e:
            _LOGGER.error(f"Failed to update traffic data: {str(e)}")
            self._attr_available = False
        else:
            self._attr_available = True

    @property
    def state(self) -> float:
        """返回总流量（MB）"""
        return self._traffic_data["total"]

    @property
    def extra_state_attributes(self) -> Dict[str, float]:
        """额外属性：显示上传/下载流量"""
        return {
            "upload_traffic_mb": self._traffic_data["upload"],
            "download_traffic_mb": self._traffic_data["download"]
        }

    @property
    def available(self) -> bool:
        return self._attr_available
