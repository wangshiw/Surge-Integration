from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
import voluptuous as vol

from .const import DOMAIN, CONF_API_KEY, CONF_URL  # 假设常量定义在 const.py 中

class SurgeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(
        self, user_input: dict = None
    ) -> FlowResult:
        errors = {}

        if user_input is not None:
            # 验证用户输入（例如检查 API Key 有效性）
            if not await self._validate_api_key(user_input[CONF_API_KEY]):
                errors["base"] = "invalid_api_key"
            else:
                # 保存配置并创建配置项
                return self.async_create_entry(
                    title="Surge Integration",
                    data=user_input
                )

        # 定义表单字段
        schema = vol.Schema({
            vol.Required(CONF_URL, default="https://api.surge.com"): str,
            vol.Required(CONF_API_KEY): str,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors
        )

    async def _validate_api_key(self, api_key: str) -> bool:
        # 实际验证逻辑（例如调用 Surge API 测试连接）
        # 示例：假设返回 True 表示验证通过
        return True
