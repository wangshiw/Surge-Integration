# Surge Integration for Home Assistant  
控制Surge代理的HTTP API，支持策略组切换、流量监控等功能。  
## 安装  
1. 通过HACS添加仓库：`[https://github.com/wangshiw/Surge-Integration]`  
2. 下载并重启Home Assistant。  
## 配置  
在`configuration.yaml`中添加：  
```yaml  
surge:  
  host: 192.168.50.29  
  api_key: abc123
  features:                   # 通用功能开关
    - mitm
    - capture
    - rewrite
    - scripting
  mac_features:               # Mac 专属功能开关
    - system_proxy
    - enhanced_mode
  update_interval: 30         # 状态刷新间隔（秒）
  use_https: false            # 是否启用 HTTPS（需 Surge 支持）
  verify_ssl: true            # 是否验证 SSL 证书（测试时可设为 false）
