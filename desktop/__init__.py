"""desktop — DSH Research Lab 桌面端（打包形态的应用层）。

模块职责：
- paths       资源定位（打包 / 开发双形态）
- config      应用配置与模型凭据（本机 0600，只写不读）
- patch_writer 生成 DSH web profile 的凭据引用 patch（无密钥）
- bootstrap   首启装配（工作台模板 → 可写主目录，skills/presets 安装）
- dsh_manager 内置 DSH web 生命周期（真实 DSH，非模拟）
- shell       pywebview 桌面窗口壳（可选依赖，缺失时回退浏览器模式）
- app         命令行入口（默认窗口；--smoke 无界面冒烟验证）
"""
