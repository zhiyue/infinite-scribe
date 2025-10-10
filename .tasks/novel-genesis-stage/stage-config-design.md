# 创世阶段配置设计方案（react-jsonschema-form 版）

## 背景

用户需要为创世阶段提供一个表单让用户选择和填写，每个阶段需要有固定的模板结构，能够在 Pydantic 校验；前端模态窗口内渲染表单，推荐采用 react-jsonschema-form（RJSF）+ AJV 校验，并用 shadcn/ui 组件做自定义 widgets，保证视觉一致性。

## 当前数据库设计分析

### 已有的数据库结构
- `GenesisStageRecord.config: JSONB` - 存储阶段配置
- `GenesisStage` 枚举 - 定义4个阶段类型（INITIAL_PROMPT, WORLDVIEW, CHARACTERS, PLOT_OUTLINE）
- `GenesisStageSession` - 管理阶段与对话会话关系

### 存在的问题
- `config` 字段是 `dict[str, Any]`，需要在服务端落库前由 Pydantic 校验/标准化
- 前端需要按阶段动态渲染表单，需从后端获取 JSON Schema 与默认模板（或从代码生成并暴露）
- 缺乏统一的 UI 渲染层，需选型并约定前端生成器（采用 RJSF）

## 设计方案：改进Schema设计

### 核心原则
**不新增数据库表**，通过代码层面的 Schema 设计解决问题。

### 理由
1. **阶段相对固定** - 4个创世阶段不会频繁变化
2. **避免过度设计** - 新增模板表会增加系统复杂度
3. **性能考虑** - 避免额外的数据库查询
4. **维护简单** - 代码定义的schema更容易版本控制

## 具体实现方案

### 1. 为每个阶段创建专门的配置 Schema（后端）

```python
# apps/backend/src/schemas/genesis/stage_config_schemas.py

from typing import Union, Type
from pydantic import BaseModel, Field
from ..enums import GenesisStage

class InitialPromptConfig(BaseModel):
    """初始提示阶段配置"""
    genre: str = Field(..., description="小说类型", example="玄幻")
    style: str = Field(..., description="写作风格", example="第三人称")
    target_word_count: int = Field(..., description="目标字数", ge=10000, le=1000000)
    special_requirements: list[str] = Field(default_factory=list, description="特殊要求列表")

    class Config:
        json_schema_extra = {
            "example": {
                "genre": "玄幻",
                "style": "第三人称",
                "target_word_count": 100000,
                "special_requirements": ["融入中国传统文化元素", "避免过于血腥的情节", "加入轻松幽默的元素"]
            }
        }

class WorldviewConfig(BaseModel):
    """世界观阶段配置"""
    time_period: str = Field(..., description="时代设定", example="古代")
    geography_type: str = Field(..., description="地理环境", example="大陆")
    tech_magic_level: str = Field(..., description="科技/魔法水平", example="高魔法")
    social_structure: str = Field(..., description="社会结构", example="封建制")
    power_system: str | None = Field(None, description="力量体系", example="修真等级")

    class Config:
        json_schema_extra = {
            "example": {
                "time_period": "古代",
                "geography_type": "大陆",
                "tech_magic_level": "高魔法",
                "social_structure": "封建制",
                "power_system": "修真等级"
            }
        }

class CharactersConfig(BaseModel):
    """角色阶段配置"""
    protagonist_count: int = Field(..., description="主角数量", ge=1, le=5)
    relationship_complexity: str = Field(..., description="角色关系复杂度", example="中等")
    personality_preferences: list[str] = Field(..., description="性格类型偏好")
    include_villains: bool = Field(True, description="是否包含反派角色")

    class Config:
        json_schema_extra = {
            "example": {
                "protagonist_count": 1,
                "relationship_complexity": "中等",
                "personality_preferences": ["坚韧", "聪明", "善良"],
                "include_villains": True
            }
        }

class PlotOutlineConfig(BaseModel):
    """情节大纲阶段配置"""
    chapter_count_preference: int = Field(..., description="章节数量偏好", ge=5, le=100)
    plot_complexity: str = Field(..., description="情节复杂度", example="中等")
    conflict_types: list[str] = Field(..., description="冲突类型")
    pacing_preference: str = Field("中等", description="节奏偏好", example="快节奏")

    class Config:
        json_schema_extra = {
            "example": {
                "chapter_count_preference": 30,
                "plot_complexity": "中等",
                "conflict_types": ["内心冲突", "人际冲突", "社会冲突"],
                "pacing_preference": "中等"
            }
        }

# 联合类型定义
StageConfigUnion = Union[InitialPromptConfig, WorldviewConfig, CharactersConfig, PlotOutlineConfig]

def get_stage_config_schema(stage: GenesisStage) -> Type[BaseModel]:
    """根据阶段类型返回对应的配置Schema"""
    mapping = {
        GenesisStage.INITIAL_PROMPT: InitialPromptConfig,
        GenesisStage.WORLDVIEW: WorldviewConfig,
        GenesisStage.CHARACTERS: CharactersConfig,
        GenesisStage.PLOT_OUTLINE: PlotOutlineConfig
    }
    return mapping[stage]

def validate_stage_config(stage: GenesisStage, config: dict) -> BaseModel:
    """验证阶段配置"""
    schema_class = get_stage_config_schema(stage)
    return schema_class(**config)
```

### 2. 更新现有的 Stage Schema（后端）

```python
# 更新 apps/backend/src/schemas/genesis/stage_schemas.py

from .stage_config_schemas import StageConfigUnion, validate_stage_config

class CreateStageRequest(BaseModel):
    """Request schema for creating a Genesis stage record."""

    stage: GenesisStage = Field(..., description="Stage type")
    config: dict[str, Any] | None = Field(default=None, description="Stage configuration")
    iteration_count: int = Field(default=0, description="Iteration count for repeated stages")

    @model_validator(mode='after')
    def validate_config_for_stage(self):
        """验证配置是否符合阶段要求"""
        if self.config is not None:
            validate_stage_config(self.stage, self.config)
        return self

class UpdateStageRequest(BaseModel):
    """Request schema for updating a Genesis stage record."""

    config: dict[str, Any] | None = Field(default=None, description="Stage configuration")

    def validate_with_stage(self, stage: GenesisStage):
        """在已知阶段类型的情况下验证配置"""
        if self.config is not None:
            validate_stage_config(stage, self.config)
```

### 3. API 端点（新增/补充）

为配合 RJSF，后端需提供：

1) 获取阶段配置 JSON Schema（RJSF `schema`）

```python
@router.get("/stages/{stage}/config/schema")
async def get_stage_config_schema(stage: GenesisStage):
    schema_class = get_stage_config_schema(stage)
    return schema_class.model_json_schema()
```

2) 获取阶段配置默认模板（RJSF `formData` 初始值）

```python
@router.get("/stages/{stage}/config/template")
async def get_stage_config_template(stage: GenesisStage):
    schema_class = get_stage_config_schema(stage)
    # 通过无参实例导出默认值（含 default/default_factory）
    return schema_class().model_dump()
```

3) 更新阶段配置（对单个阶段记录）

```python
@router.patch("/stages/{stage_id}/config")
async def update_stage_config(stage_id: UUID, payload: dict[str, Any]):
    # 读取阶段以确定 stage 类型
    record = await stage_service.get_stage_by_id(stage_id)
    if not record:
        raise HTTPException(status_code=404, detail="Stage not found")
    # Pydantic 校验与标准化
    normalized = validate_stage_config(record.stage, payload).model_dump()
    # 持久化
    updated = await stage_service.update_stage_config(db, stage_id, normalized)
    return StageResponse.model_validate(updated)
```

```python
# 新增API端点获取阶段配置模板
> 备注：如需“批量获取所有阶段 schema/template”，可提供 `/stages/config/schemas` 与 `/stages/config/templates` 的聚合端点（非必须）。
```

### 4. 前端集成（RJSF + shadcn，模态窗口）

选型：`@rjsf/core` + `@rjsf/validator-ajv8`，通过自定义 widgets/templates 将输入控件替换为 shadcn 组件（Input、Textarea 等），在 `Dialog` 中渲染。

基本数据流：
- 打开模态时并行获取：
  - `GET /api/v1/genesis/stages/{stage}/config/schema` → RJSF 的 `schema`
  - `GET /api/v1/genesis/stages/{stage}/config/template` → 作为默认 `formData`
  - `GET /api/v1/genesis/stages/{stage_id}/active-session` → 若已有历史配置，用其 `stage.config` 覆盖默认
- 点击保存：
  - `PATCH /api/v1/genesis/stages/{stage_id}/config`，body 为 RJSF 提交的 `formData`

最小使用示例：

```tsx
import Form from '@rjsf/core'
import validator from '@rjsf/validator-ajv8'

<Form schema={schema} formData={initialData} validator={validator} onSubmit={({ formData }) => save(formData)} />
```

后续可通过 `withTheme` 注入自定义 shadcn widgets/templates，以统一 UI 风格。

## 优势

1. **类型安全** - 每个阶段都有明确的配置类型
2. **前端友好** - 可以通过JSON Schema自动生成表单
3. **向后兼容** - 不改变现有数据库结构
4. **易于维护** - 配置定义在代码中，便于版本控制
5. **扩展性好** - 新增阶段或字段只需修改Schema

6. **与前端低耦合** - RJSF 直接消费后端 JSON Schema/默认值，前端逻辑最简

## 实施步骤（分层落地）

后端
- [ ] 创建 `apps/backend/src/schemas/genesis/stage_config_schemas.py`
- [ ] 在阶段服务更新/创建时接入 `validate_stage_config`
- [ ] 新增 3 个端点：获取 schema、获取 template、更新 config
- [ ] 补充单元测试（校验正确/错误用例）

前端
- [ ] 集成 `@rjsf/core` + `@rjsf/validator-ajv8`
- [ ] 在模态窗口加载 schema/template/现有 config 并渲染
- [ ] 最小自定义 widgets（Text/Textarea），逐步补齐 Select/Checkbox/Switch
- [ ] e2e/集成测试（保存成功、校验提示、回显）

## 测试策略

- 为每个阶段配置Schema编写单元测试
- 测试配置验证功能
- 集成测试API端点
- 前端表单生成和提交测试

---

## 接口契合度检查（与现有文档/实现）

已实现（见 `docs/genesis_stages_decoupling_design.md` 与代码路由）：
- `POST /api/v1/genesis/flows/{novel_id}`（创建/确保 flow 存在）
- `GET /api/v1/genesis/flows/{novel_id}`（查看流程状态，含 `current_stage_id`）
- `POST /api/v1/genesis/flows/{novel_id}/switch-stage`（切换阶段）
- `POST /api/v1/genesis/flows/{novel_id}/complete`（完成流程）
- `POST /api/v1/genesis/stages/{stage_id}/sessions`（创建/绑定会话）
- `GET /api/v1/genesis/stages/{stage_id}/sessions`（列出会话）
- `GET /api/v1/genesis/stages/{stage_id}/active-session`（返回阶段信息与活跃会话，含 `stage.config`）

缺失（为 RJSF 动态表单所必需）：
- `GET /api/v1/genesis/stages/{stage}/config/schema`（获取 JSON Schema）
- `GET /api/v1/genesis/stages/{stage}/config/template`（获取默认模板）
- `PATCH /api/v1/genesis/stages/{stage_id}/config`（提交配置变更，服务端运行 Pydantic 校验）

结论：现有文档的接口“不完全满足”RJSF 集成需求，需按本设计补充以上 3 个端点（或等价能力）。现有的 `active-session` 足以读取与回显配置；保存能力与 schema/template 获取能力需要新增。
