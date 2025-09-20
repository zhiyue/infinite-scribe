/**
 * 枚举类型定义
 * 从 shared-types 迁移而来，保持与后端 API 的一致性
 */

/**
 * Agent类型枚举
 */
export enum AgentType {
  WORLDSMITH = 'worldsmith',
  PLOTMASTER = 'plotmaster',
  OUTLINER = 'outliner',
  DIRECTOR = 'director',
  CHARACTER_EXPERT = 'character_expert',
  WORLDBUILDER = 'worldbuilder',
  WRITER = 'writer',
  CRITIC = 'critic',
  FACT_CHECKER = 'fact_checker',
  REWRITER = 'rewriter',
}

/**
 * 活动状态枚举
 */
export enum ActivityStatus {
  STARTED = 'STARTED',
  IN_PROGRESS = 'IN_PROGRESS',
  COMPLETED = 'COMPLETED',
  FAILED = 'FAILED',
  RETRYING = 'RETRYING',
}

/**
 * 工作流状态枚举
 */
export enum WorkflowStatus {
  PENDING = 'PENDING',
  RUNNING = 'RUNNING',
  COMPLETED = 'COMPLETED',
  FAILED = 'FAILED',
  CANCELLED = 'CANCELLED',
  PAUSED = 'PAUSED',
}

/**
 * 事件状态枚举
 */
export enum EventStatus {
  PENDING = 'PENDING',
  PROCESSING = 'PROCESSING',
  PROCESSED = 'PROCESSED',
  FAILED = 'FAILED',
  DEAD_LETTER = 'DEAD_LETTER',
}

/**
 * 小说状态枚举
 */
export enum NovelStatus {
  GENESIS = 'GENESIS',
  GENERATING = 'GENERATING',
  PAUSED = 'PAUSED',
  COMPLETED = 'COMPLETED',
  FAILED = 'FAILED',
}

/**
 * 章节状态枚举
 */
export enum ChapterStatus {
  DRAFT = 'DRAFT',
  REVIEWING = 'REVIEWING',
  REVISING = 'REVISING',
  PUBLISHED = 'PUBLISHED',
  FAILED = 'FAILED',
}

/**
 * 创世状态枚举
 */
export enum GenesisStatus {
  IN_PROGRESS = 'IN_PROGRESS',
  COMPLETED = 'COMPLETED',
  ABANDONED = 'ABANDONED',
  PAUSED = 'PAUSED',
}

/**
 * 创世阶段枚举
 */
export enum GenesisStage {
  INITIAL_PROMPT = 'INITIAL_PROMPT',
  WORLDVIEW = 'WORLDVIEW',
  CHARACTERS = 'CHARACTERS',
  PLOT_OUTLINE = 'PLOT_OUTLINE',
  FINISHED = 'FINISHED',
}

/**
 * 创世模式枚举
 */
export enum GenesisMode {
  /** 给我灵感模式（零输入） */
  INSPIRATION = 'inspiration',
  /** 基于想法完善模式（有输入） */
  REFINEMENT = 'refinement',
}

/**
 * 阶段会话关联状态枚举
 */
export enum StageSessionStatus {
  ACTIVE = 'ACTIVE',
  ARCHIVED = 'ARCHIVED',
  CLOSED = 'CLOSED',
}

/**
 * 操作类型枚举
 */
export enum OperationType {
  INSERT = 'INSERT',
  UPDATE = 'UPDATE',
  DELETE = 'DELETE',
}

/**
 * Genesis命令类型枚举
 * 遵循点式命名约定：Command.<Domain>.<AggregateRoot>.<OptionalSubAggregate>.<ActionInImperative>
 */
export enum GenesisCommandType {
  // Stage 0 - 创意种子
  SESSION_START = 'Command.Genesis.Session.Start',
  SEED_REQUEST = 'Command.Genesis.Session.Seed.Request',
  CONCEPT_CONFIRM = 'Command.Genesis.Session.Concept.Confirm',
  STAGE_COMPLETE = 'Command.Genesis.Session.Stage.Complete',

  // Stage 1 - 立意主题
  THEME_REQUEST = 'Command.Genesis.Session.Theme.Request',
  THEME_REVISE = 'Command.Genesis.Session.Theme.Revise',
  THEME_CONFIRM = 'Command.Genesis.Session.Theme.Confirm',

  // Stage 2 - 世界观
  WORLD_REQUEST = 'Command.Genesis.Session.World.Request',
  WORLD_UPDATE = 'Command.Genesis.Session.World.Update',
  WORLD_CONFIRM = 'Command.Genesis.Session.World.Confirm',

  // Stage 3 - 人物
  CHARACTER_REQUEST = 'Command.Genesis.Session.Character.Request',
  CHARACTER_UPDATE = 'Command.Genesis.Session.Character.Update',
  CHARACTER_CONFIRM = 'Command.Genesis.Session.Character.Confirm',
  CHARACTER_NETWORK_CREATE = 'Command.Genesis.Session.CharacterNetwork.Create',

  // Stage 4 - 情节
  PLOT_REQUEST = 'Command.Genesis.Session.Plot.Request',
  PLOT_UPDATE = 'Command.Genesis.Session.Plot.Update',
  PLOT_CONFIRM = 'Command.Genesis.Session.Plot.Confirm',

  // Stage 5 - 细节
  DETAILS_REQUEST = 'Command.Genesis.Session.Details.Request',
  DETAILS_CONFIRM = 'Command.Genesis.Session.Details.Confirm',

  // 通用命令
  SESSION_FINISH = 'Command.Genesis.Session.Finish',
  SESSION_FAIL = 'Command.Genesis.Session.Fail',
  BRANCH_CREATE = 'Command.Genesis.Session.Branch.Create',
}
