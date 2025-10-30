"""Surge Integration 配置流（UI配置）"""

import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import (
    CONF_API_KEY,
    CONF_HOST,
    CONF_PORT,
    CONF_UPDATE_INTERVAL,
    CONF_USE_HTTPS,
    CONF_VERIFY_SSL,
    DEFAULT_PORT,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_USE_HTTPS,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
)
from .surge_api import SurgeAPIClient, SurgeAPIError

_LOGGER = logging.getLogger(__name__)

# UI表单配置schema（与用户输入字段对应）
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,  # 必选：Surge设备IP（如192.168.1.100）
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): vol.Coerce(int),  # 可选：端口
        vol.Required(CONF_API_KEY): str,  # 必选：API Key（从Surge配置获取）
        vol.Optional(CONF_USE_HTTPS, default=DEFAULT_USE_HTTPS): bool,  # 可选：HTTPS
        vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,  # 可选：SSL验证
        vol.Optional(
            CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL
        ): vol.Coerce(int),  # 可选：刷新间隔
    }
)


class SurgeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Surge配置流处理类"""

    VERSION = 1  # 配置版本（用于后续迁移）
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL  # 本地轮询连接

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """处理用户首次配置步骤"""
        errors: Dict[str, str] = {}

        # 1. 若用户提交了配置（点击"提交"按钮）
        if user_input is not None:
            try:
                # 验证配置：测试与Surge的连接
                await self._validate_config(user_input)

                # 检查是否已存在相同配置（避免重复添加）
                await self.async_set_unique_id(
                    f"surge_{user_input[CONF_HOST]}_{user_input[CONF_PORT]}"
                )
                self._abort_if_unique_id_configured()

                # 配置验证通过，创建配置项
                return self.async_create_entry(
                    title=f"Surge ({user_input[CONF_HOST]})",  # UI显示的配置名称
                    data=user_input,  # 存储用户配置
                )

            # 捕获验证错误，返回对应提示
            except CannotConnect:
                errors["base"] = "cannot_connect"  # 连接失败
            except InvalidAuth:
                errors["base"] = "invalid_auth"  # API Key错误
            except SurgeAPIError:
                errors["base"] = "api_error"  # 其他API错误
            except Exception as exc:
                _LOGGER.exception(f"配置验证未知错误: {exc}")
                errors["base"] = "unknown"  # 未知错误

        # 2. 显示配置表单（首次进入或验证失败时）
        return self.async_show_form(
            step_id="user",  # 步骤ID（固定为user）
            data_schema=STEP_USER_DATA_SCHEMA,  # 表单字段定义
            errors=errors,  # 错误提示（为空则不显示）
            description_placeholders={
                "host": "Surge设备的局域网IP（如192.168.1.100）",
                "api_key": "Surge配置中http-api的Key（如xxx@0.0.0.0:6171中的xxx）",
            },
        )

    @callback
    def async_get_options_flow(
        self, config_entry: config_entries.ConfigEntry
    ) -> config_entries.OptionsFlow:
        """支持后续修改配置（可选，此处暂不实现）"""
        return SurgeOptionsFlow(config_entry)

    async def _validate_config(self, user_input: Dict[str, Any]) -> None:
        """验证用户配置：测试与Surge的API连接"""
        # 创建临时API客户端
        session = self.hass.helpers.aiohttp_client.async_get_clientsession()
        client = SurgeAPIClient(
            host=user_input[CONF_HOST],
            port=user_input[CONF_PORT],
            api_key=user_input[CONF_API_KEY],
            session=session,
            use_https=user_input[CONF_USE_HTTPS],
            verify_ssl=user_input[CONF_VERIFY_SSL],
        )

        try:
            # 测试请求：获取配置列表（验证连接和权限）
            await client.get_profiles()
        except ConnectionError as exc:
            raise CannotConnect from exc
        except ValueError as exc:
            raise InvalidAuth from exc
        except Exception as exc:
            raise SurgeAPIError from exc


class SurgeOptionsFlow(config_entries.OptionsFlow):
    """配置修改流程（暂不实现，如需支持修改可扩展）"""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """修改配置步骤（示例，可根据需求扩展）"""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(step_id="init")


# 自定义错误类（用于区分不同错误类型）
class CannotConnect(HomeAssistantError):
    """无法连接到Surge设备"""


class InvalidAuth(HomeAssistantError):
    """API Key验证失败"""


class SurgeAPIError(HomeAssistantError):
    """Surge API请求错误"""
