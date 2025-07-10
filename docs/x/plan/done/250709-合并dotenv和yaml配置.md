# 统一 dotenv 配置方案（移除 conf.yaml，引入 pydantic-settings）

## 1. 背景

DeerFlow 当前在 **后端** 依赖两种配置来源：

1. **`.env` / 环境变量**（通过 `python-dotenv` 加载；前端亦使用 `process.env`） , 示例为 .env.example
2. **`conf.yaml`**（由自定义 `load_yaml_config()` 读取）, 示例为 conf.yaml.example

双通道导致：

* 配置项重复，认知负担高
* 运行时需要保证两份文件同步更新
* YAML 缺少类型校验，易产生隐蔽错误

经讨论，决定 **彻底移除 `conf.yaml`，并使用 [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) 管理配置**：

* 单一来源：全部配置均来自环境变量（`.env` 仅作为本地便利文件）
* 类型安全：借助 Pydantic 校验与默认值支持
* 命名统一：使用 `ENV_PREFIX_` 简化获取（见 §3）

## 2. 现状梳理

### 2.1 后端（Python）

| 功能 | 关键文件 | 说明 |
| ---- | -------- | ---- |
| `.env` 加载 | `src/deerflowx/config/__init__.py`, `src/deerflowx/config/tools.py`, `src/deerflowx/prose/graph/builder.py` | `load_dotenv()` |
| YAML 加载 | `src/deerflowx/config/loader.py` | 递归替换 `$ENV_VAR` |
| LLM 配置 | `src/deerflowx/llms/llm.py` | 读取 `conf.yaml` & 覆盖 env |
| 示例 YAML | `conf.yaml.example` | 开发者参考 |

### 2.2 前端（Next.js）

前端仅依赖 `process.env`，由 `web/src/env.js` 使用 `@t3-oss/env-nextjs` + `zod` 校验；无需改动，但变量命名需保持一致。

### 2.3 DevOps

* `docker-compose.yml`: 为后端挂载 `conf.yaml` 并使用 `env_file: .env`
* CI（未来）/Dockerfile 等均依赖 `.env`

## 3. 设计方案

1. **删除 `conf.yaml` 及其全部引用**，包括 `conf.yaml.example`。
2. **采用分层 Settings 结构**：

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

# === 子配置 ===
class BasicModelSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BASIC_MODEL_")

    base_url: str = "https://api.example.com"
    model: str = "doubao-1-5-pro-32k-250115"
    api_key: str

class ReasoningModelSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="REASONING_MODEL_")

    base_url: str | None = None
    model: str | None = None
    api_key: str | None = None

# === 顶层配置 ===
class AppSettings(BaseSettings):
    # 不设置 env_prefix，顶层字段以原名读取
    model_config = SettingsConfigDict(env_prefix="")

    basic_model: BasicModelSettings = BasicModelSettings()
    reasoning_model: ReasoningModelSettings = ReasoningModelSettings()

    # 其它全局字段
    search_api: str = "tavily"  # SEARCH_API
```

* 使用方法：

```python
from deerflowx.config.settings import AppSettings
settings = AppSettings()

settings.basic_model.api_key  # 访问 BASIC_MODEL_API_KEY
settings.search_api           # 访问 SEARCH_API
```

3. **移除 `python-dotenv` 依赖**：在应用入口不再调用 `load_dotenv()`；Docker/Compose 仍可通过 `dotenv` CLI 或 shell `source` 读取本地 `.env`，但由运行时外部完成。
4. **弃用 `load_yaml_config()`**：删除 `src/deerflowx/config/loader.py` 及相关单元测试。
5. **更新业务代码**：所有对 `load_yaml_config()` 的调用改为读取 `settings` 对象。
6. **前端保持现状**：确保变量命名与后端一致，例如 `NEXT_PUBLIC_API_URL` 等。

## 4. 影响范围

### 后端
* **删除文件**：`conf.yaml`, `conf.yaml.example`, `src/deerflowx/config/loader.py`
* **修改文件**：
  * `src/deerflowx/config/__init__.py`、`tools.py`、`prose/graph/builder.py` —— 移除 `load_dotenv()`；导出 `AppSettings` 给外层引用
  * `src/deerflowx/llms/llm.py` —— 改用 `settings.basic_model__*` 获取参数
  * 其它引用 YAML 的模块
* **新增依赖**：`pydantic-settings`（已在 `pyproject.toml` 中）

### 前端
* 无代码级改变；文档更新变量命名规范。

### Docker & Compose
* **删除** `volumes: ./conf.yaml:/app/conf.yaml:ro`
* **保留** `env_file: .env`（或改用 Secrets Manager）
* 入口脚本中可选择 `dotenv -q -- <command>` 方案，确保容器内可读到 `.env`

### 测试
* 删除 / 修改涉及 YAML 的单元测试
* 新增 `settings` 相关测试

## 5. 任务拆解

| # | 模块 | 任务 | 状态 |
| -- | ---- | ---- | ---- |
| 1 | 调研 | 列出现有 YAML 使用点（已完成） | ✅ |
| 2 | Backend | 移除 `python-dotenv` 调用 | ⏳ |
| 3 | Backend | 编写 `AppSettings` 并替换所有配置读取 | ⏳ |
| 4 | Backend | 删除 YAML loader & 示例文件 | ⏳ |
| 5 | Backend | 调整单元 / 集成测试 | ⏳ |
| 6 | DevOps | 更新 Dockerfile / Compose，验证本地运行 | ⏳ |
| 7 | Docs | 更新 FAQ / README / 开发文档 | ⏳ |

## 6. 风险与缓解

| 风险 | 描述 | 缓解措施 |
| ---- | ---- | ---- |
| 环境变量缺失 | 生产环境未注入必需变量导致启动失败 | Pydantic 在启动时立即抛错；CI 添加 env 检查 step |
| 变量命名不一致 | 旧代码仍使用旧变量名 | 代码审计 + 单元测试覆盖 |
| 秘钥泄露 | `.env` 被误提交 | `.gitignore` & pre-commit 配置扫描 |

