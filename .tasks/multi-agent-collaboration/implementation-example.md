# 多Agent协作实现示例

## 场景描述

**用户需求**: "为角色Alice创建一段心理描述和对话场景"

**涉及Agent**:
1. CharacterExpertAgent - 心理分析
2. DirectorAgent - 对话场景生成
3. QualityAssuranceAgent - 质量检查和迭代优化

## 完整实现流程

### 1. API层：命令接收

```python
# apps/backend/src/api/routes/conversation.py

@router.post("/sessions/{session_id}/commands")
async def create_character_analysis_command(
    session_id: UUID,
    request: CharacterAnalysisRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> dict:
    """创建角色分析命令"""

    # 使用现有的命令服务
    command_service = ConversationCommandService()

    result = await command_service.enqueue_command(
        db=db,
        user_id=current_user.id,
        session_id=session_id,
        command_type="character.analyze_and_generate",
        payload={
            "character_id": request.character_id,
            "analysis_depth": request.analysis_depth,
            "scene_context": request.scene_context
        },
        idempotency_key=request.idempotency_key  # 前端生成UUID
    )

    return result
```

### 2. 事件处理：工作流编排

```python
# apps/backend/src/agents/orchestrator.py

class OrchestratorAgent(BaseAgent):

    async def handle_character_analysis_command(
        self,
        message: KafkaMessage
    ) -> None:
        """处理角色分析命令"""

        command_data = message.value
        command_id = UUID(command_data["command_id"])
        correlation_id = str(command_id)

        # 定义工作流步骤
        workflow_steps = [
            {
                "agent_type": "character_expert",
                "step_name": "psychological_analysis",
                "input": {
                    "character_id": command_data["payload"]["character_id"],
                    "analysis_depth": command_data["payload"]["analysis_depth"]
                }
            },
            {
                "agent_type": "director",
                "step_name": "scene_generation",
                "input": {
                    "scene_context": command_data["payload"]["scene_context"],
                    "depends_on": "psychological_analysis"  # 依赖前一步
                }
            },
            {
                "agent_type": "quality_assurance",
                "step_name": "iterative_refinement",
                "input": {
                    "max_iterations": 3,
                    "quality_threshold": 0.85
                }
            }
        ]

        # 执行工作流
        await self.execute_multi_agent_workflow(
            command_id=command_id,
            workflow_steps=workflow_steps
        )

    async def execute_multi_agent_workflow(
        self,
        command_id: UUID,
        workflow_steps: List[dict]
    ) -> None:
        """执行多Agent工作流"""

        correlation_id = str(command_id)

        # 获取顶层round信息
        session_id, parent_round_path = await self.get_command_round_info(command_id)

        for i, step in enumerate(workflow_steps, 1):
            # 创建AsyncTask
            task = await self.create_agent_task(
                command_id=command_id,
                agent_type=step["agent_type"],
                step_name=step["step_name"],
                input_data=step["input"]
            )

            # 发布Agent任务事件
            await self.publish_agent_task_event(
                correlation_id=correlation_id,
                agent_type=step["agent_type"],
                task_id=task.id,
                step_order=i
            )

            # 发布进度更新事件（前端SSE会接收）
            await self.publish_progress_event(
                correlation_id=correlation_id,
                current_step=i,
                total_steps=len(workflow_steps),
                agent_type=step["agent_type"]
            )
```

### 3. Agent实现：CharacterExpertAgent

```python
# apps/backend/src/agents/character_expert.py

class CharacterExpertAgent(BaseAgent):

    async def handle_psychological_analysis(
        self,
        message: KafkaMessage
    ) -> None:
        """处理心理分析任务"""

        task_data = message.value
        task_id = UUID(task_data["task_id"])
        correlation_id = task_data["correlation_id"]

        try:
            # 更新任务状态
            await self.update_task_status(task_id, "RUNNING", progress=10)

            # 执行心理分析
            character_id = task_data["input"]["character_id"]
            analysis_depth = task_data["input"]["analysis_depth"]

            analysis_result = await self.analyze_character_psychology(
                character_id=character_id,
                depth=analysis_depth
            )

            # 更新任务进度
            await self.update_task_status(task_id, "RUNNING", progress=80)

            # 创建Agent Round（用户可见输出）
            await self.create_agent_round(
                correlation_id=correlation_id,
                agent_type="character_expert",
                step_name="psychological_analysis",
                result=analysis_result,
                task_id=task_id
            )

            # 完成任务
            await self.update_task_status(
                task_id,
                "COMPLETED",
                progress=100,
                result=analysis_result
            )

            # 发布完成事件（触发下一个Agent）
            await self.publish_agent_completed_event(
                correlation_id=correlation_id,
                agent_type="character_expert",
                result=analysis_result
            )

        except Exception as e:
            await self.handle_agent_error(task_id, correlation_id, e)

    async def create_agent_round(
        self,
        correlation_id: str,
        agent_type: str,
        step_name: str,
        result: dict,
        task_id: UUID
    ) -> None:
        """创建Agent执行结果的Round"""

        # 获取父Round信息
        parent_round_info = await self.get_parent_round_info(correlation_id)
        session_id = parent_round_info["session_id"]
        parent_round_path = parent_round_info["round_path"]

        # 计算子Round路径
        next_step_number = await self.get_next_step_number(
            session_id,
            parent_round_path
        )
        round_path = f"{parent_round_path}.{next_step_number}"

        # 准备Round输出数据
        round_output = {
            "agent_type": agent_type,
            "agent_id": f"{agent_type}_{uuid4().hex[:8]}",
            "step": step_name,
            "result": result,
            "task_id": str(task_id),
            "metrics": {
                "execution_time_ms": self.get_execution_time(),
                "tokens_used": result.get("tokens_used", 0),
                "model": result.get("model", "unknown")
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        # 使用现有Round创建服务
        round_service = ConversationRoundCreationService()

        await round_service.create_round(
            db=self.db,
            user_id=parent_round_info["user_id"],
            session_id=session_id,
            role=DialogueRole.ASSISTANT,
            input_data={},  # Agent round主要是输出
            output_data=round_output,
            correlation_id=correlation_id,
            parent_round_path=parent_round_path
        )
```

### 4. Agent实现：DirectorAgent

```python
# apps/backend/src/agents/director.py

class DirectorAgent(BaseAgent):

    async def handle_scene_generation(
        self,
        message: KafkaMessage
    ) -> None:
        """处理场景生成任务"""

        task_data = message.value
        correlation_id = task_data["correlation_id"]

        # 获取依赖数据（CharacterExpert的分析结果）
        dependency_result = await self.get_dependency_result(
            correlation_id=correlation_id,
            dependency_agent="character_expert"
        )

        # 生成对话场景
        scene_result = await self.generate_dialogue_scene(
            character_analysis=dependency_result,
            scene_context=task_data["input"]["scene_context"]
        )

        # 创建Agent Round
        await self.create_agent_round(
            correlation_id=correlation_id,
            agent_type="director",
            step_name="scene_generation",
            result=scene_result,
            dependencies=["character_expert"]
        )

    async def get_dependency_result(
        self,
        correlation_id: str,
        dependency_agent: str
    ) -> dict:
        """获取依赖Agent的执行结果"""

        # 通过correlation_id查询依赖Agent的Round
        query = select(ConversationRound).where(
            and_(
                ConversationRound.correlation_id == correlation_id,
                ConversationRound.role == "assistant",
                ConversationRound.output["agent_type"].astext == dependency_agent
            )
        )

        result = await self.db.scalar(query)
        if not result:
            raise DependencyNotFoundError(
                f"Dependency result not found: {dependency_agent}"
            )

        return result.output["result"]
```

### 5. Agent实现：QualityAssuranceAgent（迭代优化）

```python
# apps/backend/src/agents/quality_assurance.py

class QualityAssuranceAgent(BaseAgent):

    async def handle_iterative_refinement(
        self,
        message: KafkaMessage
    ) -> None:
        """处理迭代优化任务"""

        task_data = message.value
        correlation_id = task_data["correlation_id"]
        max_iterations = task_data["input"]["max_iterations"]
        quality_threshold = task_data["input"]["quality_threshold"]

        # 获取前置结果
        previous_results = await self.get_workflow_results(correlation_id)

        # 执行迭代优化
        await self.execute_iterative_refinement(
            correlation_id=correlation_id,
            previous_results=previous_results,
            max_iterations=max_iterations,
            quality_threshold=quality_threshold
        )

    async def execute_iterative_refinement(
        self,
        correlation_id: str,
        previous_results: dict,
        max_iterations: int,
        quality_threshold: float
    ) -> None:
        """执行迭代优化过程"""

        base_round_info = await self.get_base_round_info(correlation_id)
        base_round_path = f"{base_round_info['round_path']}.3"  # QA是第3步

        for iteration in range(1, max_iterations + 1):
            # 质量评估
            quality_score = await self.assess_quality(previous_results)

            # 创建迭代Round
            iteration_round_path = f"{base_round_path}.{iteration}"

            iteration_result = {
                "iteration_number": iteration,
                "quality_score": quality_score,
                "assessment": await self.generate_quality_assessment(previous_results),
                "improvements": await self.suggest_improvements(previous_results) if quality_score < quality_threshold else None
            }

            await self.create_iteration_round(
                correlation_id=correlation_id,
                round_path=iteration_round_path,
                iteration_result=iteration_result
            )

            # 检查收敛条件
            if quality_score >= quality_threshold:
                await self.mark_workflow_completed(
                    correlation_id=correlation_id,
                    final_quality_score=quality_score
                )
                break

            # 如果需要改进，触发相关Agent重新执行
            if iteration < max_iterations:
                await self.trigger_refinement_iteration(
                    correlation_id=correlation_id,
                    improvements=iteration_result["improvements"]
                )

        # 发布工作流完成事件
        await self.publish_workflow_completed_event(correlation_id)

    async def create_iteration_round(
        self,
        correlation_id: str,
        round_path: str,
        iteration_result: dict
    ) -> None:
        """创建迭代Round"""

        parent_round_info = await self.get_parent_round_info(correlation_id)

        round_output = {
            "agent_type": "quality_assurance",
            "step": "iterative_refinement",
            "iteration_number": iteration_result["iteration_number"],
            "quality_score": iteration_result["quality_score"],
            "assessment": iteration_result["assessment"],
            "improvements": iteration_result.get("improvements"),
            "is_final": iteration_result["quality_score"] >= 0.85,
            "convergence_achieved": iteration_result["quality_score"] >= 0.85
        }

        round_service = ConversationRoundCreationService()

        await round_service.create_round(
            db=self.db,
            user_id=parent_round_info["user_id"],
            session_id=parent_round_info["session_id"],
            role=DialogueRole.ASSISTANT,
            input_data={},
            output_data=round_output,
            correlation_id=correlation_id,
            parent_round_path=parent_round_info["parent_round_path"]
        )
```

## 6. 前端展示：React组件

```typescript
// apps/frontend/src/components/MultiAgentWorkflow.tsx

interface WorkflowProgress {
  commandId: string;
  correlationId: string;
  status: 'running' | 'completed' | 'failed';
  steps: AgentStep[];
  iterations: IterationStep[];
}

interface AgentStep {
  roundPath: string;
  agentType: string;
  stepName: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  result?: any;
  metrics?: any;
}

export const MultiAgentWorkflow: React.FC<{sessionId: string, commandId: string}> = ({
  sessionId,
  commandId
}) => {
  const [progress, setProgress] = useState<WorkflowProgress | null>(null);

  useEffect(() => {
    // 订阅SSE事件
    const eventSource = new EventSource(
      `/api/sse/sessions/${sessionId}/commands/${commandId}`
    );

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.correlation_id === commandId) {
        updateWorkflowProgress(data);
      }
    };

    return () => eventSource.close();
  }, [sessionId, commandId]);

  const updateWorkflowProgress = (eventData: any) => {
    if (eventData.event_type.includes('Agent.Started')) {
      // 更新Agent状态为运行中
    }

    if (eventData.event_type.includes('Agent.Completed')) {
      // 更新Agent状态为完成
    }

    if (eventData.event_type.includes('Iteration.Created')) {
      // 添加新的迭代记录
    }
  };

  return (
    <div className="workflow-container">
      <WorkflowProgressBar progress={progress} />
      <AgentStepsList steps={progress?.steps || []} />
      <IterationHistory iterations={progress?.iterations || []} />
    </div>
  );
};
```

## 数据流总结

### Round层次结构
```
5           # 用户命令（顶层Round）
├── 5.1     # CharacterExpert分析结果
├── 5.2     # Director场景生成结果
└── 5.3     # QualityAssurance评估
    ├── 5.3.1   # 第1次迭代评估
    ├── 5.3.2   # 第2次迭代评估
    └── 5.3.3   # 最终收敛结果
```

### correlation_id链路追踪
所有相关数据都使用 `command.id` 作为 `correlation_id`:
- ConversationRound.correlation_id
- AsyncTask.correlation_id (通过triggered_by_command_id)
- DomainEvent.correlation_id
- EventOutbox.headers.correlation_id

### 事件流转
```
CommandReceived → AgentTaskCreated → AgentStarted →
AgentProgress → AgentCompleted → IterationCreated →
WorkflowCompleted
```

这个实现完全基于现有的数据模型，无需任何schema变更，充分利用了分层round和correlation_id的设计优势。