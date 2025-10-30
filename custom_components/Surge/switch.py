from typing import Dict
import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.entity import DeviceInfo

from .surge_api import SurgeAPIClient
from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

class SurgeFeatureSwitch(SwitchEntity):
    def __init__(self, api: SurgeAPIClient, feature: str, update_interval: int, is_mac_only: bool = False):
        self._api = api
        self._feature = feature  # 功能名称（如 mitm、system_proxy）
        self._is_mac_only = is_mac_only
        self._update_interval = update_interval
        self._attr_is_on = False  # 开关状态
        self._attr_unique_id = f"{DOMAIN}_{feature}_switch"
        self._attr_name = f"Surge {feature.replace('_', ' ').title()}"  # 显示名称（如 "Surge System Proxy"）
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{self._api._host}:{self._api._port}")},
            name="Surge Controller",
            model="Surge Mac" if is_mac_only else "Surge Mac/iOS",
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
        """从 API 刷新功能状态"""
        try:
            self._attr_is_on = await self._api.get_feature_status(self._feature)
        except ConnectionError:
            _LOGGER.warning(f"Could not connect to Surge (feature: {self._feature})")
            self._attr_available = False
        except Exception as e:
            if "404" in str(e) and self._is_mac_only:
                _LOGGER.warning(f"Mac-only feature {self._feature} not supported on this device")
            else:
                _LOGGER.error(f"Failed to update {self._feature} status: {str(e)}")
            self._attr_available = False
        else:
            self._attr_available = True

    async def async_turn_on(self, **kwargs) -> None:
        """启用功能"""
        try:
            await self._api.set_feature_status(self._feature, True)
            await self._coordinator.async_request_refresh()
        except Exception as e:
            _LOGGER.error(f"Failed to enable {self._feature}: {str(e)}")

    async def async_turn_off(self, **kwargs) -> None:
        """禁用功能"""
        try:
            await self._api.set_feature_status(self._feature, False)
            await self._coordinator.async_request_refresh()
        except Exception as e:
            _LOGGER.error(f"Failed to disable {self._feature}: {str(e)}")

    @property
    def is_on(self) -> bool:
        return self._attr_is_on

    @property
    def available(self) -> bool:
        return self._attr_available
