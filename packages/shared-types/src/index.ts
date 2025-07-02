/**
 * Shared TypeScript types and interfaces for Infinite Scribe
 * 
 * These types correspond to the Pydantic models defined in Python files:
 * - Database models (models_db.py)
 * - API models (models_api.py) 
 * - Event models (events.py)
 */

// TODO: Task 4 - 在此文件中定义对应的TypeScript接口
// 确保类型与Pydantic模型保持一致

/**
 * 基础数据库模型接口
 */
export interface BaseDBModel {
  // 通用字段将在 Task 4 中定义
}

/**
 * 基础API模型接口
 */
export interface BaseAPIModel {
  // API模型字段将在 Task 4 中定义
}

/**
 * 基础事件接口
 */
export interface BaseEvent {
  event_id: string;
  event_type: string;
  timestamp: string;
  source_agent: string;
  novel_id: string;
  correlation_id?: string;
}

// 核心实体接口将在 Task 4 中实现:
// - Novel
// - WorldviewEntry
// - Character
// - StoryArc
// - ChapterVersion
// - GenesisSession
// - GenesisStep
// - AgentActivity
// - WorkflowRun
// - Event
// - AgentConfiguration

// API请求/响应接口将在 Task 4 中实现:
// - CreateNovelRequest
// - CreateNovelResponse
// - GenesisStepRequest
// - GenesisStepResponse

// 事件接口将在 Task 4 中实现:
// - NovelCreatedEvent
// - GenesisStepCompletedEvent
// - CharacterCreatedEvent

export const VERSION = "0.1.0";