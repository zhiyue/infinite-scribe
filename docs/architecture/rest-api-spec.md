# REST API Spec
```yaml
openapi: 3.0.0
info:
  title: 多智能体网络小说自动写作系统 - 控制API
  version: v1.5.0 
  description: |
    用于前端UI与后端工作流系统交互的控制API。
    
    ## 创世流程说明
    新的创世流程包含以下阶段：
    1. **CONCEPT_SELECTION** - 立意选择与迭代阶段
    2. **STORY_CONCEPTION** - 故事构思阶段
    3. **WORLDVIEW** - 世界观创建阶段
    4. **CHARACTERS** - 角色设定阶段
    5. **PLOT_OUTLINE** - 情节大纲阶段
    6. **FINISHED** - 完成阶段
    
    ## 异步处理模式
    AI agent 交互操作（立意生成、故事构思等）采用异步处理模式：
    1. 客户端发起请求，服务器立即返回任务ID (202 Accepted)
    2. 客户端通过SSE订阅实时进度和结果推送
    3. 服务器通过SSE推送处理进度、阶段更新和最终结果
    4. 客户端可通过任务状态端点查询任务详情

    前两个阶段支持用户反馈和迭代优化，每次迭代都是异步处理。

    ## SSE最佳实践
    - **连接管理**: 支持按session_id和task_id灵活订阅
    - **进度粒度**: 合理的进度更新频率，避免过度推送
    - **断线重连**: 客户端自动重连机制，任务状态持久化
    - **错误处理**: 实时错误反馈和重试建议
    - **心跳机制**: 定期心跳保持连接活跃
servers:
  - url: http://localhost:8000/api/v1 
    description: 本地开发服务器
  - url: https://your-production-domain.com/api/v1 
    description: 生产环境服务器

components:
  schemas:
    Novel:
      type: object
      properties:
        id:
          type: string
          format: uuid
          description: 小说的唯一标识符 (UUID)
        title:
          type: string
          description: 小说标题
        theme:
          type: string
          description: 小说主题
        writing_style:
          type: string
          description: 小说写作风格
        status:
          type: string
          enum: [GENESIS, GENERATING, PAUSED, COMPLETED, FAILED]
          description: 小说的当前状态
        target_chapters:
          type: integer
          description: 目标总章节数
        completed_chapters:
          type: integer
          description: 已完成的章节数
        created_at:
          type: string
          format: date-time
          description: 创建时间戳
        updated_at:
          type: string
          format: date-time
          description: 最后更新时间戳
    Chapter:
      type: object
      properties:
        id:
          type: string
          format: uuid
          description: 章节的唯一标识符 (UUID)
        novel_id:
          type: string
          format: uuid
          description: 所属小说的ID
        chapter_number:
          type: integer
          description: 章节序号
        title:
          type: string
          description: 章节标题
        content_url:
          type: string
          format: url
          description: 指向Minio中存储的章节文本内容的URL
        status:
          type: string
          enum: [DRAFT, REVIEWING, REVISING, PUBLISHED]
          description: 章节的当前状态
        word_count:
          type: integer
          description: 章节字数
        created_at:
          type: string
          format: date-time
          description: 创建时间戳
        updated_at:
          type: string
          format: date-time
          description: 最后更新时间戳
    Review:
      type: object
      properties:
        id:
          type: string
          format: uuid
          description: 评审记录的唯一标识符 (UUID)
        chapter_id:
          type: string
          format: uuid
          description: 被评审章节的ID
        agent_id:
          type: string
          description: 执行评审的Agent的ID
        review_type:
          type: string
          enum: [CRITIC, FACT_CHECK]
          description: 评审类型
        score:
          type: number
          format: float
          description: 评论家评分 (可选)
        comment:
          type: string
          description: 评论家评语 (可选)
        is_consistent:
          type: boolean
          description: 事实核查员判断是否一致 (可选)
        issues_found:
          type: array
          items:
            type: string
          description: 事实核查员发现的问题列表 (可选)
        created_at:
          type: string
          format: date-time
          description: 评审创建时间戳
    WorldviewNode: 
      type: object
      properties:
        id: 
          type: string 
          description: Neo4j内部节点ID
        app_id: 
          type: string
          format: uuid
          description: 对应PostgreSQL中的实体ID
        labels: 
          type: array
          items: 
            type: string 
          description: 节点的标签 (e.g., Character, Location)
        properties: 
          type: object
          description: 节点的属性 (e.g., name, entry_type)
    WorldviewRelationship: 
      type: object
      properties:
        id: 
          type: string
          description: Neo4j内部关系ID
        type: 
          type: string
          description: 关系的类型 (e.g., KNOWS, LOCATED_IN)
        startNodeAppId: 
          type: string
          format: uuid
          description: 关系起始节点的app_id
        endNodeAppId: 
          type: string
          format: uuid
          description: 关系结束节点的app_id
        properties: 
          type: object
          description: 关系的属性
    ConceptTemplate:
      type: object
      properties:
        id:
          type: string
          format: uuid
          description: 立意模板唯一标识符
        core_idea:
          type: string
          description: 核心抽象思想，如"知识与无知的深刻对立"
        description:
          type: string
          description: 立意的深层含义阐述
        philosophical_depth:
          type: string
          description: 哲学思辨的深度表达
        emotional_core:
          type: string
          description: 情感核心与内在冲突
        philosophical_category:
          type: string
          description: 哲学类别，如"存在主义"、"人道主义"
        thematic_tags:
          type: array
          items:
            type: string
          description: 主题标签数组
        complexity_level:
          type: string
          enum: [simple, medium, complex]
          description: 思辨复杂度
        usage_count:
          type: integer
          description: 被选择使用的次数统计
        average_rating:
          type: number
          format: float
          description: 平均用户评分
    GenesisStartRequest:
      type: object
      required:
        - user_preferences
      properties:
        user_preferences:
          type: object
          description: 用户偏好设定，如题材、风格、复杂度等
          properties:
            preferred_genres:
              type: array
              items:
                type: string
              description: 偏好的题材类型
            complexity_preference:
              type: string
              enum: [simple, medium, complex]
              description: 思辨复杂度偏好
            emotional_themes:
              type: array
              items:
                type: string
              description: 期望的情感主题
    GenesisStartResponse:
      type: object
      properties:
        novel_id:
          type: string
          format: uuid
          description: 新创建的小说的ID
        genesis_session_id:
          type: string
          format: uuid
          description: 用于后续创世步骤的会话ID
        current_stage:
          type: string
          enum: [CONCEPT_SELECTION]
          description: 当前创世阶段
    ConceptSelectionRequest:
      type: object
      properties:
        selected_concept_ids:
          type: array
          items:
            type: integer
          description: 用户选择的立意临时ID列表
        user_feedback:
          type: string
          description: 用户对立意的反馈和要求
        action:
          type: string
          enum: [iterate, confirm]
          description: 下一步操作：继续迭代或确认立意
    StoryConceptionRequest:
      type: object
      properties:
        user_feedback:
          type: string
          description: 用户对故事构思的反馈
        specific_adjustments:
          type: object
          description: 具体调整要求
        action:
          type: string
          enum: [refine, confirm]
          description: 下一步操作：优化或确认故事构思
    GenesisStepRequest: 
      type: object
      properties:
        data:
          type: object 
          description: 具体步骤的数据，如世界观条目数组或角色对象数组
    AsyncTaskResponse:
      type: object
      properties:
        task_id:
          type: string
          format: uuid
          description: 异步任务ID，用于跟踪进度
        message:
          type: string
          description: 任务启动确认消息
        sse_endpoint:
          type: string
          description: SSE端点URL，用于接收实时进度
    ConceptGenerationResponse:
      type: object
      properties:
        step_type:
          type: string
          enum: [ai_generation, concept_refinement]
          description: 步骤类型
        generated_concepts:
          type: array
          items:
            type: object
            properties:
              temp_id:
                type: integer
                description: 临时ID，用于用户选择
              core_idea:
                type: string
                description: 核心抽象思想
              description:
                type: string
                description: 立意描述
              philosophical_depth:
                type: string
                description: 哲学深度
              emotional_core:
                type: string
                description: 情感核心
        iteration_count:
          type: integer
          description: 当前迭代次数
    StoryConceptionResponse:
      type: object
      properties:
        step_type:
          type: string
          enum: [story_generation, story_refinement]
          description: 步骤类型
        story_concept:
          type: object
          properties:
            title_suggestions:
              type: array
              items:
                type: string
              description: 标题建议
            core_concept:
              type: string
              description: 核心故事概念
            main_themes:
              type: array
              items:
                type: string
              description: 主要主题
            target_audience:
              type: string
              description: 目标读者群体
            estimated_length:
              type: string
              description: 预计长度
            genre_suggestions:
              type: array
              items:
                type: string
              description: 题材建议
        iteration_count:
          type: integer
          description: 当前迭代次数
    SSEProgressEvent:
      type: object
      properties:
        event:
          type: string
          enum: [task_started, progress_update, concept_generation_complete, story_conception_complete, task_complete, task_error]
          description: 事件类型
        data:
          type: object
          description: 事件数据
          properties:
            task_id:
              type: string
              format: uuid
              description: 任务ID
            session_id:
              type: string
              format: uuid
              description: 会话ID
            progress:
              type: number
              format: float
              minimum: 0
              maximum: 1
              description: 进度百分比 (0.0-1.0)
            message:
              type: string
              description: 进度描述信息
            stage:
              type: string
              description: 当前处理阶段
            result:
              type: object
              description: 处理结果（仅在完成事件中）
            error:
              type: object
              description: 错误信息（仅在错误事件中）
    GenesisStepResponse:
      type: object
      properties:
        success:
          type: boolean
          description: 操作是否成功
        message:
          type: string
          description: 相关的状态或错误信息
        current_stage:
          type: string
          enum: [CONCEPT_SELECTION, STORY_CONCEPTION, WORLDVIEW, CHARACTERS, PLOT_OUTLINE, FINISHED]
          description: 当前创世阶段
        next_stage:
          type: string
          description: 下一个阶段（如果有）
    WorkflowStatus:
      type: object
      properties:
        task_id:
          type: string
          description: 被查询的工作流任务ID
        status:
          type: string
          description: 工作流的当前状态
        progress:
          type: number
          format: float
          description: 工作流的完成进度 (0.0 到 1.0)
        details:
          type: string
          description: 关于当前状态的详细描述
    Metrics:
      type: object
      properties:
        total_words_generated:
          type: integer
          description: 系统生成的总字数
        cost_per_10k_words:
          type: number
          format: float
          description: 每生成一万字的平均成本
        avg_chapter_generation_time_seconds:
          type: number
          format: float
          description: 生成一个章节的平均耗时（秒）
        chapter_revision_rate:
          type: number
          format: float
          description: 章节需要修订的比例
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
      description: 用于API认证的JWT令牌

security:
  - BearerAuth: []

paths:
  /health:
    get:
      summary: 健康检查
      description: 检查API服务及其依赖项（如数据库）是否正常运行。
      responses:
        '200':
          description: 服务正常
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
                    example: ok
  /genesis/start:
    post:
      summary: 启动新的创世流程
      description: 开始一个新的小说项目，创建初始记录并返回会话ID。新流程从立意选择阶段开始。
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/GenesisStartRequest'
      responses:
        '201':
          description: 创世流程已成功启动
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/GenesisStartResponse'
        '400':
          description: 无效请求，例如请求体格式错误
  /genesis/{session_id}/concepts/generate:
    post:
      summary: 异步生成立意选项
      description: |
        基于用户偏好异步生成抽象哲学立意选项。该操作会立即返回任务ID，
        实际生成过程通过SSE推送进度和结果。
      parameters:
        - name: session_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
          description: 创世会话ID
      responses:
        '202':
          description: 立意生成任务已启动
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AsyncTaskResponse'
        '400':
          description: 请求无效或会话状态不正确
  /genesis/{session_id}/concepts/select:
    post:
      summary: 异步提交立意选择
      description: |
        用户选择立意并提供反馈，可选择继续迭代或确认立意。
        如果选择迭代，将异步处理优化过程并通过SSE推送结果。
      parameters:
        - name: session_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
          description: 创世会话ID
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ConceptSelectionRequest'
      responses:
        '200':
          description: 立意确认成功，可进入下一阶段
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/GenesisStepResponse'
        '202':
          description: 立意优化任务已启动
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AsyncTaskResponse'
  /genesis/{session_id}/story/generate:
    post:
      summary: 异步生成故事构思
      description: |
        基于确认的立意异步生成具体的故事框架和构思。
        生成过程通过SSE推送进度和结果。
      parameters:
        - name: session_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
          description: 创世会话ID
      responses:
        '202':
          description: 故事构思生成任务已启动
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AsyncTaskResponse'
        '400':
          description: 请求无效或会话状态不正确
  /genesis/{session_id}/story/refine:
    post:
      summary: 异步优化故事构思
      description: |
        根据用户反馈优化或确认故事构思。
        如果选择优化，将异步处理并通过SSE推送结果。
      parameters:
        - name: session_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
          description: 创世会话ID
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/StoryConceptionRequest'
      responses:
        '200':
          description: 故事构思确认成功，可进入下一阶段
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/GenesisStepResponse'
        '202':
          description: 故事构思优化任务已启动
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AsyncTaskResponse'
  /genesis/{session_id}/worldview:
    post:
      summary: 提交世界观设定
      description: 在创世流程中，基于确认的故事构思设计并保存世界观设定。
      parameters:
        - name: session_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
          description: 创世会话ID
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/GenesisStepRequest' 
      responses:
        '200':
          description: 世界观已保存
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/GenesisStepResponse'
  /genesis/{session_id}/characters:
    post:
      summary: 提交核心角色
      description: 在创世流程中，基于世界观和故事构思设计并保存核心角色设定。
      parameters:
        - name: session_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
          description: 创世会话ID
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/GenesisStepRequest' 
      responses:
        '200':
          description: 核心角色已保存
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/GenesisStepResponse'
  /genesis/{session_id}/plot:
    post:
      summary: 提交初始剧情弧光
      description: 在创世流程中，基于角色设定和故事构思制定并保存初始的剧情大纲或故事弧。
      parameters:
        - name: session_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
          description: 创世会话ID
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/GenesisStepRequest' 
      responses:
        '200':
          description: 初始剧情已保存
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/GenesisStepResponse'
  /genesis/{session_id}/finish:
    post:
      summary: 完成并结束创世流程
      description: 标记创世流程结束，小说项目状态变为待生成。
      parameters:
        - name: session_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
          description: 创世会话ID
      responses:
        '200':
          description: 创世已完成，小说待生成
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/GenesisStepResponse'
  /genesis/{session_id}/status:
    get:
      summary: 获取创世会话状态
      description: 获取当前创世会话的状态和进度信息。
      parameters:
        - name: session_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
          description: 创世会话ID
      responses:
        '200':
          description: 成功获取会话状态
          content:
            application/json:
              schema:
                type: object
                properties:
                  session_id:
                    type: string
                    format: uuid
                    description: 会话ID
                  current_stage:
                    type: string
                    enum: [CONCEPT_SELECTION, STORY_CONCEPTION, WORLDVIEW, CHARACTERS, PLOT_OUTLINE, FINISHED]
                    description: 当前阶段
                  status:
                    type: string
                    enum: [IN_PROGRESS, COMPLETED, ABANDONED]
                    description: 会话状态
                  confirmed_concepts:
                    type: array
                    description: 已确认的立意
                  confirmed_story_concept:
                    type: object
                    description: 已确认的故事构思
  /concept-templates:
    get:
      summary: 获取立意模板
      description: 获取可用的立意模板列表，支持筛选和排序。
      parameters:
        - name: category
          in: query
          schema:
            type: string
          description: 按哲学类别筛选
        - name: complexity
          in: query
          schema:
            type: string
            enum: [simple, medium, complex]
          description: 按复杂度筛选
        - name: limit
          in: query
          schema:
            type: integer
            default: 20
          description: 返回数量限制
      responses:
        '200':
          description: 成功获取立意模板
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/ConceptTemplate'
  /novels: 
    get:
      summary: 获取所有小说项目列表
      description: 返回当前用户的所有小说项目及其基本信息。
      responses:
        '200':
          description: 成功获取小说列表
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Novel'
  /novels/{novel_id}/generate-chapter:
    post:
      summary: 触发指定小说生成下一章
      description: 接受请求，并异步启动一个用于生成指定小说下一章的工作流。
      parameters:
        - name: novel_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
          description: 要生成章节的小说的ID
      responses:
        '202':
          description: 章节生成任务已接受，正在后台处理
          content:
            application/json:
              schema:
                type: object
                properties:
                  task_id: 
                    type: string
                    description: 启动的后台工作流任务ID，可用于查询状态
                  message:
                    type: string
                    description: 确认消息
  /chapters/{chapter_id}:
    get:
      summary: 获取指定章节内容及其评审
      description: 返回特定章节的详细信息，包括其内容和所有相关的评审记录。
      parameters:
        - name: chapter_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
          description: 要获取详情的章节ID
      responses:
        '200':
          description: 成功获取章节详情
          content:
            application/json:
              schema:
                type: object
                properties:
                  chapter:
                    $ref: '#/components/schemas/Chapter'
                  reviews:
                    type: array
                    items:
                      $ref: '#/components/schemas/Review'
  /workflows/{workflow_run_id}/status:
    get:
      summary: 查询指定工作流的状态
      description: 根据从触发任务时获取的ID，查询后台工作流的实时状态。
      parameters:
        - name: workflow_run_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
          description: 要查询状态的工作流运行ID
      responses:
        '200':
          description: 成功获取工作流状态
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/WorkflowStatus'
  /metrics:
    get:
      summary: 获取系统关键性能与成本指标
      description: 返回关于系统整体性能和成本的关键指标。
      responses:
        '200':
          description: 成功获取指标
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Metrics'
  /novels/{novel_id}/graph/worldview: 
    get:
      summary: 获取指定小说的世界观图谱数据 (用于可视化)
      description: 从Neo4j中查询并返回特定小说的知识图谱数据，用于前端进行可视化展示。
      parameters:
        - name: novel_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
          description: 要获取图谱数据的小说ID
      responses:
        '200':
          description: 成功获取图谱数据
          content:
            application/json:
              schema:
                type: object
                properties:
                  nodes:
                    type: array
                    items:
                      $ref: '#/components/schemas/WorldviewNode'
                  relationships:
                    type: array
                    items:
                      $ref: '#/components/schemas/WorldviewRelationship'
  /agents/configurations:
    get:
      summary: 获取所有 Agent 的当前配置
      description: 返回系统中所有Agent的配置信息。
      responses:
        '200':
          description: 成功获取配置列表
    post:
      summary: 更新 Agent 配置
      description: 批量或单个更新Agent的配置项。
      responses:
        '200':
          description: 配置已更新
  /agents/{agent_type}/configurations:
    get:
      summary: 获取特定 Agent 的配置历史
      description: 返回指定类型Agent的所有配置及其历史记录。
      parameters:
        - name: agent_type
          in: path
          required: true
          schema:
            type: string
          description: 要查询配置的Agent类型
      responses:
        '200':
          description: 成功获取特定Agent的配置
  /events/stream:
    get:
      summary: 订阅实时事件流 (SSE)
      description: |
        与此端点建立一个持久连接以接收服务器发送的实时事件。
        客户端应使用 EventSource API 来消费此流。
        事件将包含事件类型 (event) 和JSON数据 (data)。
      security:
        - BearerAuth: []
      parameters:
        - name: session_id
          in: query
          schema:
            type: string
            format: uuid
          description: 订阅特定创世会话的事件（可选）
        - name: task_id
          in: query
          schema:
            type: string
            format: uuid
          description: 订阅特定任务的事件（可选）
      responses:
        '200':
          description: 成功建立事件流连接。
          content:
            text/event-stream:
              schema:
                type: string
                example: |
                  event: task_started
                  data: {"task_id": "uuid-...", "session_id": "uuid-...", "message": "开始生成立意选项..."}

                  event: progress_update
                  data: {"task_id": "uuid-...", "session_id": "uuid-...", "progress": 0.3, "message": "正在分析用户偏好...", "stage": "preference_analysis"}

                  event: progress_update
                  data: {"task_id": "uuid-...", "session_id": "uuid-...", "progress": 0.6, "message": "正在生成哲学立意...", "stage": "concept_generation"}

                  event: concept_generation_complete
                  data: {"task_id": "uuid-...", "session_id": "uuid-...", "progress": 1.0, "result": {"step_type": "ai_generation", "generated_concepts": [...]}}

                  event: story_conception_complete
                  data: {"task_id": "uuid-...", "session_id": "uuid-...", "progress": 1.0, "result": {"step_type": "story_generation", "story_concept": {...}}}

                  event: task_error
                  data: {"task_id": "uuid-...", "session_id": "uuid-...", "error": {"code": "GENERATION_FAILED", "message": "立意生成失败"}}

                  event: workflow_status_update
                  data: {"workflow_run_id": "uuid-...", "status": "RUNNING", "details": "DirectorAgent is processing..."}

                  event: chapter_status_update
                  data: {"chapter_id": "uuid-...", "status": "REVIEWING"}
        '401':
          description: 未经授权
  /genesis/tasks/{task_id}/status:
    get:
      summary: 查询创世任务状态
      description: 查询特定创世任务的当前状态和进度。
      parameters:
        - name: task_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
          description: 任务ID
      responses:
        '200':
          description: 成功获取任务状态
          content:
            application/json:
              schema:
                type: object
                properties:
                  task_id:
                    type: string
                    format: uuid
                    description: 任务ID
                  session_id:
                    type: string
                    format: uuid
                    description: 关联的会话ID
                  status:
                    type: string
                    enum: [PENDING, RUNNING, COMPLETED, FAILED]
                    description: 任务状态
                  progress:
                    type: number
                    format: float
                    description: 进度百分比 (0.0-1.0)
                  stage:
                    type: string
                    description: 当前处理阶段
                  message:
                    type: string
                    description: 状态描述
                  result:
                    type: object
                    description: 任务结果（仅在完成时）
                  error:
                    type: object
                    description: 错误信息（仅在失败时）
                  created_at:
                    type: string
                    format: date-time
                    description: 任务创建时间
                  updated_at:
                    type: string
                    format: date-time
                    description: 最后更新时间
        '404':
          description: 任务未找到
```
