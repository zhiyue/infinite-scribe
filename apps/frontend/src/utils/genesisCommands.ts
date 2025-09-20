/**
 * Genesis命令工具函数
 * 处理创世阶段的命令类型映射和payload构造
 *
 * ## Payload字段说明
 *
 * ### 标准化字段 (符合LLD文档要求)
 * - `user_input`: 用户输入内容，统一标准字段名
 * - `session_id`: 会话ID
 * - `stage`: 当前创世阶段
 * - `user_id`: 用户ID，通常由后端从认证上下文推导
 * - `context`: 上下文信息（迭代次数、偏好设置等）
 * - `preferences`: 用户偏好设置（针对特定命令类型）
 *
 * ### 字段标准化完成
 * 已完全迁移到使用标准的user_input字段，移除了冗余的content字段。
 * UI组件现在统一使用payload.user_input获取用户输入内容。
 *
 * @see .tasks/novel-genesis-stage/lld/command-types.md
 */

import { GenesisStage, GenesisCommandType } from '@/types/enums'

/**
 * 根据创世阶段获取对应的用户消息命令类型
 * 用于用户在当前阶段发送消息时的命令类型选择
 */
export function getCommandTypeByStage(stage: GenesisStage): GenesisCommandType {
  switch (stage) {
    case GenesisStage.INITIAL_PROMPT:
      return GenesisCommandType.SEED_REQUEST
    case GenesisStage.WORLDVIEW:
      return GenesisCommandType.WORLD_REQUEST
    case GenesisStage.CHARACTERS:
      return GenesisCommandType.CHARACTER_REQUEST
    case GenesisStage.PLOT_OUTLINE:
      return GenesisCommandType.PLOT_REQUEST
    case GenesisStage.FINISHED:
      // 已完成阶段仍然可以进行详细讨论
      return GenesisCommandType.DETAILS_REQUEST
    default:
      // 默认使用种子请求命令
      return GenesisCommandType.SEED_REQUEST
  }
}

/**
 * 构造创世命令的payload
 * 根据命令类型和用户输入构造符合文档要求的payload结构
 */
export function buildGenesisCommandPayload(
  commandType: GenesisCommandType,
  userInput: string,
  sessionId: string,
  stage: GenesisStage,
  context?: Record<string, any>
): Record<string, any> {
  const basePayload = {
    session_id: sessionId,
    user_input: userInput,
    stage: stage,
    context: context || {},
    // Note: user_id will be filled by backend from authentication context
    // If needed for specific use cases, uncomment and provide:
    // user_id: context?.user_id,
  }

  switch (commandType) {
    case GenesisCommandType.SEED_REQUEST:
      return {
        ...basePayload,
        preferences: context?.preferences || {},
        // user_id: 通常由后端从认证上下文推导，如需显式提供可取消注释
        // user_id: context?.user_id,
        context: {
          previous_attempts: context?.previous_attempts || 0,
          iteration_number: context?.iteration_number || 1,
          ...context
        }
      }

    case GenesisCommandType.WORLD_REQUEST:
    case GenesisCommandType.CHARACTER_REQUEST:
    case GenesisCommandType.PLOT_REQUEST:
    case GenesisCommandType.DETAILS_REQUEST:
      return {
        ...basePayload,
        requirements: context?.requirements || {},
        context: {
          iteration_number: context?.iteration_number || 1,
          ...context
        }
      }

    case GenesisCommandType.THEME_REQUEST:
      return {
        ...basePayload,
        theme_preferences: context?.theme_preferences || {},
        context: {
          iteration_number: context?.iteration_number || 1,
          ...context
        }
      }

    case GenesisCommandType.CONCEPT_CONFIRM:
    case GenesisCommandType.THEME_CONFIRM:
    case GenesisCommandType.WORLD_CONFIRM:
    case GenesisCommandType.CHARACTER_CONFIRM:
    case GenesisCommandType.PLOT_CONFIRM:
    case GenesisCommandType.DETAILS_CONFIRM:
      return {
        ...basePayload,
        user_feedback: userInput,
        modifications: context?.modifications || {}
      }

    case GenesisCommandType.SESSION_START:
      return {
        user_id: context?.user_id,
        initial_input: userInput,
        preferences: context?.preferences || {}
      }

    case GenesisCommandType.STAGE_COMPLETE:
      return {
        session_id: sessionId,
        current_stage: stage,
        completion_notes: userInput || ''
      }

    default:
      return basePayload
  }
}

/**
 * 获取阶段的确认命令类型
 * 用于用户确认当前阶段内容时的命令类型
 */
export function getConfirmCommandTypeByStage(stage: GenesisStage): GenesisCommandType {
  switch (stage) {
    case GenesisStage.INITIAL_PROMPT:
      return GenesisCommandType.CONCEPT_CONFIRM
    case GenesisStage.WORLDVIEW:
      return GenesisCommandType.WORLD_CONFIRM
    case GenesisStage.CHARACTERS:
      return GenesisCommandType.CHARACTER_CONFIRM
    case GenesisStage.PLOT_OUTLINE:
      return GenesisCommandType.PLOT_CONFIRM
    case GenesisStage.FINISHED:
      return GenesisCommandType.DETAILS_CONFIRM
    default:
      return GenesisCommandType.CONCEPT_CONFIRM
  }
}

/**
 * 获取阶段的更新命令类型
 * 用于用户修改当前阶段内容时的命令类型
 */
export function getUpdateCommandTypeByStage(stage: GenesisStage): GenesisCommandType {
  switch (stage) {
    case GenesisStage.INITIAL_PROMPT:
      // 初始阶段没有专门的更新命令，使用修订主题命令作为通用修改
      return GenesisCommandType.THEME_REVISE
    case GenesisStage.WORLDVIEW:
      return GenesisCommandType.WORLD_UPDATE
    case GenesisStage.CHARACTERS:
      return GenesisCommandType.CHARACTER_UPDATE
    case GenesisStage.PLOT_OUTLINE:
      return GenesisCommandType.PLOT_UPDATE
    case GenesisStage.FINISHED:
      // 完成阶段可以使用细节请求进行修改
      return GenesisCommandType.DETAILS_REQUEST
    default:
      return GenesisCommandType.THEME_REVISE
  }
}

/**
 * 判断是否为确认类型的命令
 */
export function isConfirmCommand(commandType: GenesisCommandType): boolean {
  return [
    GenesisCommandType.CONCEPT_CONFIRM,
    GenesisCommandType.THEME_CONFIRM,
    GenesisCommandType.WORLD_CONFIRM,
    GenesisCommandType.CHARACTER_CONFIRM,
    GenesisCommandType.PLOT_CONFIRM,
    GenesisCommandType.DETAILS_CONFIRM
  ].includes(commandType)
}

/**
 * 判断是否为请求类型的命令
 */
export function isRequestCommand(commandType: GenesisCommandType): boolean {
  return [
    GenesisCommandType.SEED_REQUEST,
    GenesisCommandType.THEME_REQUEST,
    GenesisCommandType.WORLD_REQUEST,
    GenesisCommandType.CHARACTER_REQUEST,
    GenesisCommandType.PLOT_REQUEST,
    GenesisCommandType.DETAILS_REQUEST
  ].includes(commandType)
}

/**
 * 获取命令类型的显示名称
 */
export function getCommandTypeDisplayName(commandType: GenesisCommandType): string {
  const displayNames: Record<GenesisCommandType, string> = {
    [GenesisCommandType.SESSION_START]: '开始会话',
    [GenesisCommandType.SEED_REQUEST]: '请求创意种子',
    [GenesisCommandType.CONCEPT_CONFIRM]: '确认概念',
    [GenesisCommandType.STAGE_COMPLETE]: '完成阶段',
    [GenesisCommandType.THEME_REQUEST]: '请求主题',
    [GenesisCommandType.THEME_REVISE]: '修订主题',
    [GenesisCommandType.THEME_CONFIRM]: '确认主题',
    [GenesisCommandType.WORLD_REQUEST]: '请求世界观',
    [GenesisCommandType.WORLD_UPDATE]: '更新世界观',
    [GenesisCommandType.WORLD_CONFIRM]: '确认世界观',
    [GenesisCommandType.CHARACTER_REQUEST]: '请求角色',
    [GenesisCommandType.CHARACTER_UPDATE]: '更新角色',
    [GenesisCommandType.CHARACTER_CONFIRM]: '确认角色',
    [GenesisCommandType.CHARACTER_NETWORK_CREATE]: '创建角色关系网',
    [GenesisCommandType.PLOT_REQUEST]: '请求情节',
    [GenesisCommandType.PLOT_UPDATE]: '更新情节',
    [GenesisCommandType.PLOT_CONFIRM]: '确认情节',
    [GenesisCommandType.DETAILS_REQUEST]: '请求细节',
    [GenesisCommandType.DETAILS_CONFIRM]: '确认细节',
    [GenesisCommandType.SESSION_FINISH]: '完成会话',
    [GenesisCommandType.SESSION_FAIL]: '会话失败',
    [GenesisCommandType.BRANCH_CREATE]: '创建分支'
  }

  return displayNames[commandType] || commandType
}