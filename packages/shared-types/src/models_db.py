"""
Database models for PostgreSQL tables

All models correspond to database tables and use snake_case field names
to match PostgreSQL conventions.
"""

from pydantic import BaseModel

# TODO: Task 3 - 在此文件中实现所有数据库表对应的Pydantic模型
# 参考: docs/architecture/database-schema.md


class BaseDBModel(BaseModel):
    """数据库模型基类"""

    model_config = {"from_attributes": True, "validate_assignment": True}


# 核心实体模型将在 Task 3 中实现
# - NovelModel
# - WorldviewEntryModel
# - CharacterModel
# - StoryArcModel
# - ChapterVersionModel
# - GenesisSessionModel
# - GenesisStepModel
# - AgentActivityModel
# - WorkflowRunModel
# - EventModel
# - AgentConfigurationModel
