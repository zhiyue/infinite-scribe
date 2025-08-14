# Event Naming Conventions

**核心原则:** 系统中的所有事件都必须是**领域事件（Domain Events）**。它们描述的是在业务领域中**已经发生的事实**，而不是技术实现或未来的指令。事件日志是系统的不可变历史记录，只追加、不修改。

## 1. 命名公式与聚合根 (Naming Formula & Aggregate Root)

所有事件名称必须严格遵循以下结构，并以**真正的聚合根（Aggregate Root）**为核心：

**`<Domain>.<AggregateRoot>.<OptionalSubAggregate>.<ActionInPastTense>`**

- **`<Domain>` (领域):** 事件所属的最高层级业务上下文。
  - **示例:** `Genesis`, `Novel`, `Chapter`, `Character`, `KnowledgeBase`, `Workflow`
- **`<AggregateRoot>` (聚合根):** 事件所直接关联的、具有独立生命周期的核心业务实体。**这是事件命名的锚点。**
  - **示例:** `Session` (对于创世流程), `Novel` (对于小说本身), `Chapter` (对于章节)
- **`<OptionalSubAggregate>` (可选子聚合/实体):** (可选) 用于提高可读性，描述与聚合根紧密相关，但在该事件中是焦点的实体。
  - **示例:** `Concept`, `Outline`, `Draft`, `Critique`
- **`<ActionInPastTense>` (过去式动作):** 描述已经发生的具体动作。**必须使用官方动词表中的词汇**。

**示例修正 (P0.1):**

- **旧:** `Genesis.ConceptGenerationRequested` (不准确，`Concept`不是根)
- **新:** `Genesis.Session.ConceptGenerationRequested` (准确，事件挂载在`GenesisSession`这个聚合根上)
- **旧:** `Chapter.CritiqueCompleted` (可接受，但可以更精确)
- **新:** `Chapter.Review.CritiqueCompleted` (更佳，明确了`Critique`是`Review`的一部分)

## 2. 官方动词表 (Controlled Verb Vocabulary)

为避免歧义和写法不一，所有`<ActionInPastTense>`**必须**从以下官方动词表中选择。

| 动词 (Verb)     | 含义                                                 | 适用场景示例                        |
| :-------------- | :--------------------------------------------------- | :---------------------------------- |
| **`Requested`** | 一个异步流程或操作**被请求**启动。                   | `Chapter.GenerationRequested`       |
| **`Created`**   | 一个**新的实体**被首次创建并持久化。                 | `Character.ProfileCreated`          |
| **`Proposed`**  | AI或系统**提出了一个草案**或建议，等待决策。         | `Genesis.Session.ConceptProposed`   |
| **`Submitted`** | 用户**提交了**一份数据或反馈。                       | `Genesis.Session.FeedbackSubmitted` |
| **`Confirmed`** | 一个草案或阶段被用户**最终确认**。                   | `Genesis.Session.StageConfirmed`    |
| **`Updated`**   | 一个已存在实体的**一个或多个属性**发生了变更。       | `Character.ProfileUpdated`          |
| **`Revised`**   | 一个已存在的草案（如章节）被**修订并生成了新版本**。 | `Chapter.DraftRevised`              |
| **`Completed`** | 一个定义明确的、有始有终的**任务或评审**已完成。     | `Chapter.Review.CritiqueCompleted`  |
| **`Finished`**  | 一个**完整的、多阶段的业务流程**已成功结束。         | `Genesis.Session.Finished`          |
| **`Failed`**    | 一个任务或流程因错误而**异常中止**。                 | `Workflow.TaskFailed`               |

## 3. 事件版本化策略 (Event Versioning Strategy)

为应对未来业务发展带来的事件结构变更，我们采用**字段版本化**策略，而非名称版本化。

- **策略:** 每个事件在`domain_events`表中都有一个`event_version`字段（默认为1）。
- **演进:**
  - 当需要对事件的`payload`进行**非破坏性变更**（如增加一个可选字段）时，可以直接修改，`event_version`**保持不变**。
  - 当需要进行**破坏性变更**（如删除字段、修改字段类型）时，**必须创建一个新的事件类型**，并将其`event_version`**递增为2**。例如，`Chapter.DraftCreated` (v1) -> `Chapter.DraftCreated` (v2)。
- **消费者责任:** 事件消费者必须能够识别和处理它们所知道的事件版本。对于不认识的新版本，它们应该优雅地忽略或记录警告。
- **禁止:** 严禁使用在事件名称后加`.v2`后缀的方式进行版本管理。

## 4. 强制事件结构 (Mandatory Event Structure)

所有发布到`domain_events`表的事件，其`payload`和`metadata`**必须**包含以下核心上下文字段，以便于追踪和关联。

- `event_id`: 事件自身的唯一标识符。
- `aggregate_id`: 事件所属聚合根的ID。
- `aggregate_type`: 事件所属聚合根的类型。
- `correlation_id`: 标识一个完整的业务流程（例如，从用户点击到所有副作用完成）。
- `causation_id`: 指向触发此事件的上一个事件的`event_id`，形成因果链。

- **说明:** 具体的`<ActionInPastTense>`体现在消息的`event_type`字段中，由消费者进行过滤，而不是通过不同的Topic来区分。

## 5. 处理复合动作 (Handling Compound Actions)

当一个操作在逻辑上需要更新多个聚合根时，**必须**将其拆分为多个独立的、原子的领域事件。

- **推荐模式:** 每个聚合根的变更都发布一个自己的事件。例如，一个动作既更新了角色，又推进了故事线，则应发布两个事件：`Character.ProfileUpdated` 和 `Novel.StorylineProgressed`。
- **编排:** 由上游的业务逻辑（如Prefect Flow）来保证这两个事件的发布。
- **避免:** 避免创建一个模糊的、如`System.StateChanged`的事件，然后在`payload`里塞入大量不同实体的变更。这会破坏事件的单一事实原则。

## 6. 死信队列 (Dead-Letter Queue - DLQ)

- **策略:** 所有事件消费者在处理事件失败后，**必须**采用带有**指数退避（Exponential Backoff）**策略的重试机制（例如，重试3次，间隔为1s, 2s, 4s）。
- **最终失败:** 如果达到最大重试次数后仍然失败，消费者**必须**将这个“毒丸”消息，连同最后的错误信息和堆栈跟踪，一起发送到一个专用的死信队列主题（如 `domain-events.dlq`）。
- **确认机制:** 消费者应采用**手动ACK**模式。只有在事件被成功处理（或成功发送到DLQ）后，才向Kafka确认消息消费，以防止消息丢失。
