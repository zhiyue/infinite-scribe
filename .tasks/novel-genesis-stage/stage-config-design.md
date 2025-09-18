# 创世阶段配置设计方案

## 背景

用户需要为创世阶段提供一个表单让用户选择和填写，每个阶段需要有固定的模板结构，能够在Pydantic校验。

## 当前数据库设计分析

### 已有的数据库结构
- `GenesisStageRecord.config: JSONB` - 存储阶段配置
- `GenesisStage` 枚举 - 定义4个阶段类型（INITIAL_PROMPT, WORLDVIEW, CHARACTERS, PLOT_OUTLINE）
- `GenesisStageSession` - 管理阶段与对话会话关系

### 存在的问题
- `config` 字段是 `dict[str, Any]`，无法提供 Pydantic 校验
- 前端无法知道每个阶段需要什么配置字段
- 缺乏类型安全

## 设计方案：改进Schema设计

### 核心原则
**不新增数据库表**，通过代码层面的Schema设计解决问题。

### 理由
1. **阶段相对固定** - 4个创世阶段不会频繁变化
2. **避免过度设计** - 新增模板表会增加系统复杂度
3. **性能考虑** - 避免额外的数据库查询
4. **维护简单** - 代码定义的schema更容易版本控制

## 具体实现方案

### 1. 为每个阶段创建专门的配置Schema

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

### 2. 更新现有的Stage Schema

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

### 3. API端点改进

```python
# 新增API端点获取阶段配置模板
@router.get("/stages/{stage}/config-schema")
async def get_stage_config_schema(stage: GenesisStage):
    """获取指定阶段的配置Schema"""
    schema_class = get_stage_config_schema(stage)
    return schema_class.model_json_schema()

@router.get("/stages/config-schemas")
async def get_all_stage_config_schemas():
    """获取所有阶段的配置Schema"""
    return {
        stage.value: get_stage_config_schema(stage).model_json_schema()
        for stage in GenesisStage
        if stage != GenesisStage.FINISHED
    }
```

### 4. 前端集成

前端可以通过API获取Schema，动态生成表单：

```typescript
// 获取阶段配置Schema
const getStageConfigSchema = async (stage: GenesisStage) => {
  const response = await api.get(`/genesis/stages/${stage}/config-schema`);
  return response.data;
};

// 根据Schema生成表单组件
const StageConfigForm = ({ stage, onSubmit }) => {
  const [schema, setSchema] = useState(null);

  useEffect(() => {
    getStageConfigSchema(stage).then(setSchema);
  }, [stage]);

  if (!schema) return <Loading />;

  return <JsonSchemaForm schema={schema} onSubmit={onSubmit} />;
};
```

## 优势

1. **类型安全** - 每个阶段都有明确的配置类型
2. **前端友好** - 可以通过JSON Schema自动生成表单
3. **向后兼容** - 不改变现有数据库结构
4. **易于维护** - 配置定义在代码中，便于版本控制
5. **扩展性好** - 新增阶段或字段只需修改Schema

## 实施步骤

1. 创建 `stage_config_schemas.py` 文件
2. 更新现有的 `stage_schemas.py`
3. 添加新的API端点
4. 前端集成JSON Schema表单生成器
5. 编写单元测试验证各阶段配置

## 测试策略

- 为每个阶段配置Schema编写单元测试
- 测试配置验证功能
- 集成测试API端点
- 前端表单生成和提交测试