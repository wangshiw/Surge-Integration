"""Surge 选择实体（配置/出站模式/策略组）"""

import logging
from typing import List, Optional, Dict

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, API_CLIENT
from .__init__ import get_common_device_info
from .surge_api import SurgeAPIClient, SurgeAPIError

_LOGGER = logging.getLogger(__name__)


# ------------------------------ 配置选择实体 ------------------------------
class SurgeProfileSelect(SelectEntity):
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
        self._options: List[str] = []
        self._current_option: Optional[str] = None

        # 实体基础属性
        self._attr_unique_id = f"{entry.entry_id}_profile_select"
        self._attr_name = "Surge 活跃配置"
        self._attr_device_info = get_common_device_info(entry)  # 统一设备信息
        self._attr_available = True

        # 初始化更新协调器（定时刷新状态）
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
        """从API刷新配置列表和当前配置"""
        try:
            self._options = await self._api_client.get_profiles()
            self._current_option = await self._api_client.get_current_profile()
        except Exception as exc:
            _LOGGER.error(f"更新配置列表失败: {str(exc)}")
            self._attr_available = False
        else:
            self._attr_available = True

    @property
    def options(self) -> List[str]:
        """返回可用配置列表"""
        return self._options

    @property
    def current_option(self) -> Optional[str]:
        """返回当前配置"""
        return self._current_option

    async def async_select_option(self, option: str) -> None:
        """切换到指定配置"""
        try:
            await self._api_client.switch_profile(option)
            await self._coordinator.async_request_refresh()  # 立即刷新状态
        except Exception as exc:
            _LOGGER.error(f"切换配置{option}失败: {str(exc)}")


# ------------------------------ 出站模式选择实体 ------------------------------
class SurgeOutboundSelect(SelectEntity):
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
        self._options = ["direct", "proxy", "rule"]  # 固定出站模式选项
        self._current_option: Optional[str] = None

        self._attr_unique_id = f"{entry.entry_id}_outbound_select"
        self._attr_name = "Surge 出站模式"
        self._attr_device_info = get_common_device_info(entry)
        self._attr_available = True

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
        try:
            self._current_option = await self._api_client.get_outbound_mode()
        except Exception as exc:
            _LOGGER.error(f"更新出站模式失败: {str(exc)}")
            self._attr_available = False
        else:
            self._attr_available = True

    @property
    def options(self) -> List[str]:
        return self._options

    @property
    def current_option(self) -> Optional[str]:
        return self._current_option

    async def async_select_option(self, option: str) -> None:
        try:
            await self._api_client.set_outbound_mode(option)
            await self._coordinator.async_request_refresh()
        except Exception as exc:
            _LOGGER.error(f"切换出站模式{option}失败: {str(exc)}")


# ------------------------------ 策略组选择实体 ------------------------------
class SurgePolicyGroupSelect(SelectEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api_client: SurgeAPIClient,
        update_interval: int,
        group_name: str,
    ):
        self.hass = hass
        self.entry = entry
        self._api_client = api_client
        self._update_interval = update_interval
        self._group_name = group_name  # 当前策略组名称
        self._options: List[str] = []
        self._current_option: Optional[str] = None

        self._attr_unique_id = f"{entry.entry_id}_policy_group_{group_name.lower().replace(' ', '_')}"
        self._attr_name = f"Surge 策略组 - {group_name}"
        self._attr_device_info = get_common_device_info(entry)
        self._attr_available = True

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
        try:
            self._options = await self._api_client.get_policy_group_policies(self._group_name)
            self._current_option = await self._api_client.get_policy_group_current_policy(self._group_name)
        except Exception as exc:
            _LOGGER.error(f"更新策略组{self._group_name}失败: {str(exc)}")
            self._attr_available = False
        else:
            self._attr_available = True

    @property
    def options(self) -> List[str]:
        return self._options

    @property
    def current_option(self) -> Optional[str]:
        return self._current_option

    async def async_select_option(self, option: str) -> None:
        try:
            await self._api_client.set_policy_group_policy(self._group_name, option)
            await self._coordinator.async_request_refresh()
        except Exception as exc:
            _LOGGER.error(f"策略组{self._group_name}切换到{option}失败: {str(exc)}")


# ------------------------------ 平台注册入口 ------------------------------
async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """从Config Entry注册选择实体"""
    # 从全局存储获取API客户端和配置
    domain_data = hass.data[DOMAIN][entry.entry_id]
    api_client = domain_data[API_CLIENT]
    update_interval = entry.data[CONF_UPDATE_INTERVAL]

    entities = []

    # 1. 添加配置选择实体
    entities.append(SurgeProfileSelect(hass, entry, api_client, update_interval))

    # 2. 添加出站模式选择实体
    entities.append(SurgeOutboundSelect(hass, entry, api_client, update_interval))

    # 3. 动态添加策略组实体（获取所有策略组并创建对应实体）
    try:
        policy_groups = await api_client.get_policy_groups()
        for group in policy_groups:
            entities.append(
                SurgePolicyGroupSelect(hass, entry, api_client, update_interval, group)
            )
        _LOGGER.info(f"成功加载{len(policy_groups)}个策略组实体")
    except Exception as exc:
        _LOGGER.warning(f"加载策略组实体失败: {str(exc)}")

    # 注册所有实体
    async_add_entities(entities, update_before_add=True)
