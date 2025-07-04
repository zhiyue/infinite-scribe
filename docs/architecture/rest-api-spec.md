# REST API Spec

```yaml
openapi: 3.0.0
info:
  title: 多智能体网络小说自动写作系统 - 控制API
  version: 2.2.0
  description: |
    用于前端UI与后端工作流系统交互的、基于命令驱动和状态查询的控制API。
    
    ## 核心交互模式
    1.  **发起操作:** 所有需要后台处理的用户意图，都通过向一个统一的命令端点 `POST /.../commands` 发送一个**命令**来完成。
    2.  **异步处理:** 对于耗时的操作（如AI生成），API会立即返回 `202 Accepted`，表示命令已被接收。
    3.  **实时更新:** 客户端应通过 `GET /events/stream` 订阅服务器发送事件（SSE），以接收所有任务的实时进度和状态更新。
    4.  **状态恢复:** 当UI需要恢复一个流程（如用户刷新页面）时，它应调用对应的状态查询端点（如 `GET /genesis/sessions/{id}/state`）来获取完整的当前上下文。

components:
  schemas:
    # --- Command & Task Schemas ---
    CommandRequest:
      type: object
      required: [command_type]
      properties:
        command_type:
          type: string
          description: "命令的唯一类型标识, e.g., 'RequestConceptGeneration', 'ConfirmStage'"
        payload:
          type: object
          description: "与命令相关的具体数据"
    CommandResponse:
      type: object
      properties:
        command_id:
          type: string
          format: uuid
          description: "被创建的命令的唯一ID"
        message:
          type: string
          description: "确认消息"
    AsyncTask:
      type: object
      properties:
        id:
          type: string
          format: uuid
        task_type:
          type: string
        status:
          type: string
          enum: [PENDING, RUNNING, COMPLETED, FAILED, CANCELLED]
        progress:
          type: number
          format: float
        result_data:
          type: object
        error_data:
          type: object
        created_at:
          type: string
          format: date-time
        updated_at:
          type: string
          format: date-time

    # --- Genesis Schemas ---
    GenesisSessionState:
      type: object
      properties:
        session_id:
          type: string
          format: uuid
        current_stage:
          type: string
          enum: [CONCEPT_SELECTION, STORY_CONCEPTION, WORLDVIEW, CHARACTERS, PLOT_OUTLINE, FINISHED]
        is_pending:
          type: boolean
          description: "当前会话是否正在等待一个后台任务或命令完成"
        pending_command_type:
          type: string
          nullable: true
          description: "如果is_pending为true, 当前等待的命令类型"
        confirmed_data:
          type: object
          description: "已确认的各阶段数据"
        last_result:
          type: object
          nullable: true
          description: "上一个完成的AI任务的结果，供UI展示"

    # --- Novel & Chapter Schemas ---
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
        agent_type:
          type: string
          description: 执行评审的Agent的类型
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
    ChapterDetail:
      type: object
      properties:
        chapter:
          $ref: '#/components/schemas/Chapter'
        reviews:
          type: array
          items:
            $ref: '#/components/schemas/Review'

    # --- Knowledge Base & Metrics Schemas ---
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

security:
  - BearerAuth: []

paths:
  /health:
    get:
      summary: 健康检查
      description: 检查API服务及其依赖项是否正常运行。
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

  # ================= GENESIS WORKFLOW =================
  /genesis/sessions:
    post:
      summary: 启动一个新的创世会话
      description: 开始一个新的小说项目，创建会话记录，并返回会话ID。
      responses:
        '201':
          description: 会话成功创建
          content:
            application/json:
              schema:
                type: object
                properties:
                  session_id:
                    type: string
                    format: uuid

  /genesis/sessions/{session_id}/state:
    get:
      summary: 获取或恢复一个创世会话的状态
      description: 当UI需要恢复创世流程时调用，以获取完整的当前上下文。
      parameters:
        - name: session_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: 创世会话的当前状态
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/GenesisSessionState'
        '404':
          description: 会话未找到

  /genesis/sessions/{session_id}/commands:
    post:
      summary: 向创世会话发送一个命令
      description: |
        这是创世流程中所有用户意图的统一入口。
        - 对于异步命令 (如 `RequestConceptGeneration`), 返回 202 Accepted。
        - 对于同步命令 (如 `ConfirmStage`), 返回 200 OK。
      parameters:
        - name: session_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CommandRequest'
      responses:
        '200':
          description: 同步命令成功执行
        '202':
          description: 异步命令已接受，正在后台处理
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CommandResponse'
        '409':
          description: 冲突。例如，当一个同类型的命令已在处理中时。

  # ================= NOVEL & CHAPTER WORKFLOWS =================
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

  /novels/{novel_id}/commands:
    post:
      summary: 向指定小说发送一个命令
      description: 用于触发针对已存在小说的操作，如“生成下一章”。
      parameters:
        - name: novel_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CommandRequest'
      responses:
        '202':
          description: 异步命令已接受
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CommandResponse'

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
      responses:
        '200':
          description: 成功获取章节详情
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ChapterDetail'

  /novels/{novel_id}/graph/worldview: 
    get:
      summary: 获取指定小说的世界观图谱数据 (用于可视化)
      description: 从Neo4j中查询并返回特定小说的知识图谱数据。
      parameters:
        - name: novel_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
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

  # ================= GENERIC & UTILITY ENDPOINTS =================
  /tasks/{task_id}:
    get:
      summary: 查询指定异步任务的状态
      description: (可选的回退方案) 如果SSE连接中断，可以用此接口轮询任务状态。
      parameters:
        - name: task_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: 任务详情
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AsyncTask'

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

  /events/stream:
    get:
      summary: 订阅实时事件流 (SSE)
      description: |
        与此端点建立一个持久连接以接收服务器发送的实时事件。
        可以通过查询参数过滤你感兴趣的事件源。
      parameters:
        - name: context_id
          in: query
          schema:
            type: string
            format: uuid
          description: "只订阅与此上下文ID（如session_id）相关的事件"
      responses:
        '200':
          description: 成功建立事件流连接。
          content:
            text/event-stream:
              schema:
                type: string
                example: |
                  event: genesis.state.updated
                  data: {"session_id": "...", "current_stage": "STORY_CONCEPTION", "is_pending": false}

                  event: task.progress.updated
                  data: {"task_id": "...", "progress": 50.0, "message": "正在分析角色关系..."}
```

