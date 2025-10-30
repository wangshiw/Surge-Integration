"""Surge 流量监控实体（适配Config Flow）"""

import logging
from typing import Dict, Optional

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.const import UnitOfDataVolume

from .const import (
    DOMAIN,
    API_CLIENT,
    CONF_UPDATE_INTERVAL,
)
from .__init__ import get_common_device_info
from .surge_api import SurgeAPIClient, SurgeAPIError

_LOGGER = logging.getLogger(__name__)


class SurgeTrafficSensor(SensorEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api_client: SurgeAPIClient,
        update_interval: int,
    ):
        self.hass = hass
        self.entry = entry
        self._api_client = api_client
        self._update_interval = update_interval
        self._traffic_data: Dict[str, float] = {
            "upload": 0.0,
            "download": 0.0,
            "total": 0.0,
        }

        # 实体基础属性
        self._attr_unique_id = f"{entry.entry_id}_traffic_sensor"
        self._attr_name = "Surge 总流量"
        self._attr_unit_of_measurement = UnitOfDataVolume.MEGABYTES  # 单位：MB
        self._attr_state_class = SensorStateClass.TOTAL  # 累计型传感器
        self._attr_device_info = get_common_device_info(entry)  # 统一设备信息
        self._attr_available = True

        # 初始化更新协调器
        self._coordinator = DataUpdateCoordinator(
            self.hass,
            _LOGGER,
            name=self._attr_name,
            update_method=self._async_update_data,
            update_interval=self._update_interval,
        )

    async def async_added_to_hass(self) -> None:
        """实体添加到HA时启动协调器"""
        await super().async_added_to_hass()
        await self._coordinator.async_config_entry_first_refresh()

    async def _async_update_data(self) -> None:
        """从API刷新流量数据"""
        try:
            self._traffic_data = await self._api_client.get_traffic()
        except Exception as exc:
            _LOGGER.error(f"更新流量数据失败: {str(exc)}")
            self._attr_available = False
        else:
            self._attr_available = True

    @property
    def state(self) -> Optional[float]:
        """返回总流量（MB）"""
        return self._traffic_data["total"]

    @property
    def extra_state_attributes(self) -> Dict[str, float]:
        """额外属性：显示上传/下载流量"""
        return {
            "上传流量(MB)": self._traffic_data["upload"],
            "下载流量(MB)": self._traffic_data["download"],
        }

    @property
    def available(self) -> bool:
        """返回实体是否可用"""
        return self._attr_available


# ------------------------------ 平台注册入口 ------------------------------
async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """从Config Entry注册流量传感器实体"""
    # 从全局存储获取API客户端
    domain_data = hass.data[DOMAIN][entry.entry_id]
    api_client = domain_data[API_CLIENT]
    update_interval = entry.data[CONF_UPDATE_INTERVAL]

    # 创建并注册流量传感器实体
    async_add_entities(
        [SurgeTrafficSensor(hass, entry, api_client, update_interval)],
        update_before_add=True,
    )
