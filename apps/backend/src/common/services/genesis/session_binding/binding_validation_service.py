"""Genesis会话绑定验证服务

提供会话绑定的安全验证和一致性检查。
"""

from uuid import UUID

from src.common.repositories.genesis.flow_repository import GenesisFlowRepository
from src.common.repositories.conversation.session_repository import ConversationSessionRepository
from src.models.conversation import ConversationSession
from src.models.genesis_flows import GenesisFlow


class BindingValidationService:
    """会话绑定验证服务"""

    def __init__(
        self,
        flow_repository: GenesisFlowRepository,
        conversation_session_repository: ConversationSessionRepository,
    ):
        self.flow_repository = flow_repository
        self.conversation_session_repository = conversation_session_repository

    async def validate_session_binding(
        self,
        session_id: UUID,
        flow_id: UUID,
    ) -> tuple[ConversationSession, GenesisFlow]:
        """
        验证会话是否可以绑定到指定的Genesis流程。

        Args:
            session_id: 会话ID
            flow_id: Genesis流程ID

        Returns:
            验证通过的会话和流程实例元组

        Raises:
            ValueError: 如果验证失败，包含具体错误信息
        """
        # 获取会话
        session = await self.conversation_session_repository.find_by_id(session_id)
        if not session:
            raise ValueError(f"Conversation session with ID {session_id} not found")

        # 获取流程
        flow = await self.flow_repository.find_by_id(flow_id)
        if not flow:
            raise ValueError(f"Genesis flow with ID {flow_id} not found")

        # 执行绑定校验
        self._validate_scope_type(session)
        self._validate_scope_id(session, flow)

        return session, flow

    async def validate_session_for_novel(
        self,
        session_id: UUID,
        novel_id: UUID,
    ) -> ConversationSession:
        """
        验证会话是否属于指定的小说。

        Args:
            session_id: 会话ID
            novel_id: 小说ID

        Returns:
            验证通过的会话实例

        Raises:
            ValueError: 如果验证失败
        """
        # 获取会话
        session = await self.conversation_session_repository.find_by_id(session_id)
        if not session:
            raise ValueError(f"Conversation session with ID {session_id} not found")

        # 验证会话属于指定小说
        self._validate_scope_type(session)
        if session.scope_id != str(novel_id):
            raise ValueError(
                f"Session scope_id '{session.scope_id}' does not match novel_id '{novel_id}'"
            )

        return session

    def _validate_scope_type(self, session: ConversationSession) -> None:
        """
        验证会话的scope_type是否为GENESIS。

        Args:
            session: 会话实例

        Raises:
            ValueError: 如果scope_type不是GENESIS
        """
        if session.scope_type != "GENESIS":
            raise ValueError(
                f"Cannot bind session with scope_type '{session.scope_type}' to Genesis stage. "
                "Only GENESIS sessions can be bound to Genesis stages."
            )

    def _validate_scope_id(self, session: ConversationSession, flow: GenesisFlow) -> None:
        """
        验证会话的scope_id是否与流程的novel_id匹配。

        Args:
            session: 会话实例
            flow: Genesis流程实例

        Raises:
            ValueError: 如果scope_id与novel_id不匹配
        """
        if session.scope_id != str(flow.novel_id):
            raise ValueError(
                f"Session scope_id '{session.scope_id}' does not match "
                f"flow novel_id '{flow.novel_id}'. "
                "Sessions can only be bound to flows of the same novel."
            )

    async def check_binding_conflicts(
        self,
        session_id: UUID,
        flow_id: UUID,
    ) -> list[str]:
        """
        检查绑定可能存在的冲突。

        Args:
            session_id: 会话ID
            flow_id: 流程ID

        Returns:
            冲突警告列表，空列表表示无冲突
        """
        warnings = []

        try:
            session, flow = await self.validate_session_binding(session_id, flow_id)

            # 检查会话状态
            if session.status != "ACTIVE":
                warnings.append(f"Session status is '{session.status}', not 'ACTIVE'")

            # 检查流程状态
            if flow.status.value != "IN_PROGRESS":
                warnings.append(f"Flow status is '{flow.status.value}', not 'IN_PROGRESS'")

            # 可以添加更多检查...

        except ValueError as e:
            warnings.append(str(e))

        return warnings