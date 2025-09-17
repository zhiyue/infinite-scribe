"""Integration tests for Genesis API endpoints.

测试Genesis阶段解耦后的API端点功能。
"""

import pytest
from httpx import AsyncClient
from uuid import UUID

from src.schemas.enums import GenesisStatus, GenesisStage, StageStatus, StageSessionStatus


@pytest.mark.integration
class TestGenesisEndpointsIntegration:
    """Genesis API端点的集成测试"""

    @pytest.mark.asyncio
    async def test_ensure_genesis_flow_creates_new_flow(self, async_client: AsyncClient, auth_headers, test_novel):
        """测试确保Genesis流程存在 - 创建新流程"""
        # Arrange
        novel_id = test_novel.id

        # Act - 创建Genesis流程
        response = await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}",
            headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["novel_id"] == str(novel_id)
        assert data["status"] == GenesisStatus.IN_PROGRESS.value
        assert data["current_stage"] == GenesisStage.INITIAL_PROMPT.value
        assert data["version"] == 1
        assert isinstance(data["state"], dict)
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    @pytest.mark.asyncio
    async def test_ensure_genesis_flow_returns_existing_flow(self, async_client: AsyncClient, auth_headers, test_novel):
        """测试确保Genesis流程存在 - 返回现有流程"""
        # Arrange - 先创建一个流程
        novel_id = test_novel.id
        first_response = await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}",
            headers=auth_headers
        )
        first_flow = first_response.json()

        # Act - 再次调用应该返回相同的流程
        second_response = await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}",
            headers=auth_headers
        )

        # Assert
        assert second_response.status_code == 200
        second_flow = second_response.json()
        assert first_flow["id"] == second_flow["id"]
        assert first_flow["version"] == second_flow["version"]

    @pytest.mark.asyncio
    async def test_get_genesis_flow_with_stages(self, async_client: AsyncClient, auth_headers, test_novel):
        """测试获取Genesis流程详情及其阶段"""
        # Arrange - 创建流程和阶段
        novel_id = test_novel.id

        # 创建流程
        flow_response = await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}",
            headers=auth_headers
        )

        # 创建阶段
        stage_response = await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}/stages/{GenesisStage.INITIAL_PROMPT.value}",
            json={"config": {"test": "data"}},
            headers=auth_headers
        )

        # Act
        get_response = await async_client.get(
            f"/api/v1/genesis/flows/{novel_id}",
            headers=auth_headers
        )

        # Assert
        assert get_response.status_code == 200
        data = get_response.json()
        assert "flow" in data
        assert "stages" in data
        assert data["flow"]["novel_id"] == str(novel_id)
        assert len(data["stages"]) == 1
        assert data["stages"][0]["stage"] == GenesisStage.INITIAL_PROMPT.value

    @pytest.mark.asyncio
    async def test_update_genesis_flow_advance_stage(self, async_client: AsyncClient, auth_headers, test_novel):
        """测试更新Genesis流程 - 推进阶段"""
        # Arrange
        novel_id = test_novel.id

        # 创建流程
        flow_response = await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}",
            headers=auth_headers
        )
        flow = flow_response.json()

        # Act - 推进到下一阶段
        update_data = {
            "current_stage": GenesisStage.WORLDVIEW.value,
            "state": {"progress": "advanced"},
            "expected_version": flow["version"]
        }
        update_response = await async_client.put(
            f"/api/v1/genesis/flows/{novel_id}",
            json=update_data,
            headers=auth_headers
        )

        # Assert
        assert update_response.status_code == 200
        updated_flow = update_response.json()
        assert updated_flow["current_stage"] == GenesisStage.WORLDVIEW.value
        assert updated_flow["state"]["progress"] == "advanced"
        assert updated_flow["version"] == flow["version"] + 1

    @pytest.mark.asyncio
    async def test_create_genesis_stage(self, async_client: AsyncClient, auth_headers, test_novel):
        """测试创建Genesis阶段"""
        # Arrange
        novel_id = test_novel.id

        # 创建流程
        flow_response = await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}",
            headers=auth_headers
        )

        # Act - 创建阶段
        stage_data = {
            "config": {
                "theme": "science fiction",
                "style": "hard sf"
            }
        }
        stage_response = await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}/stages/{GenesisStage.WORLDVIEW.value}",
            json=stage_data,
            headers=auth_headers
        )

        # Assert
        assert stage_response.status_code == 201
        stage = stage_response.json()
        assert stage["stage"] == GenesisStage.WORLDVIEW.value
        assert stage["status"] == StageStatus.RUNNING.value
        assert stage["config"]["theme"] == "science fiction"
        assert stage["iteration_count"] == 0

    @pytest.mark.asyncio
    async def test_get_genesis_stage_with_sessions(self, async_client: AsyncClient, auth_headers, test_novel):
        """测试获取Genesis阶段及其会话"""
        # Arrange
        novel_id = test_novel.id

        # 创建流程和阶段
        await async_client.post(f"/api/v1/genesis/flows/{novel_id}", headers=auth_headers)
        stage_response = await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}/stages/{GenesisStage.INITIAL_PROMPT.value}",
            json={"config": {}},
            headers=auth_headers
        )
        stage = stage_response.json()
        stage_id = stage["id"]

        # Act
        get_response = await async_client.get(
            f"/api/v1/genesis/stages/{stage_id}",
            headers=auth_headers
        )

        # Assert
        assert get_response.status_code == 200
        data = get_response.json()
        assert "stage" in data
        assert "sessions" in data
        assert data["stage"]["id"] == stage_id
        assert isinstance(data["sessions"], list)

    @pytest.mark.asyncio
    async def test_create_stage_session_new_session(self, async_client: AsyncClient, auth_headers, test_novel):
        """测试创建阶段会话关联 - 创建新会话"""
        # Arrange
        novel_id = test_novel.id

        # 创建流程和阶段
        await async_client.post(f"/api/v1/genesis/flows/{novel_id}", headers=auth_headers)
        stage_response = await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}/stages/{GenesisStage.INITIAL_PROMPT.value}",
            json={"config": {}},
            headers=auth_headers
        )
        stage = stage_response.json()
        stage_id = stage["id"]

        # Act - 创建新会话并绑定
        session_data = {
            "is_primary": True,
            "session_kind": "user_interaction"
        }
        session_response = await async_client.post(
            f"/api/v1/genesis/stages/{stage_id}/sessions",
            json=session_data,
            headers=auth_headers
        )

        # Assert
        assert session_response.status_code == 201
        association = session_response.json()
        assert association["stage_id"] == stage_id
        assert association["is_primary"] is True
        assert association["session_kind"] == "user_interaction"
        assert association["status"] == StageSessionStatus.ACTIVE.value
        assert "session_id" in association

    @pytest.mark.asyncio
    async def test_list_stage_sessions(self, async_client: AsyncClient, auth_headers, test_novel):
        """测试列出阶段会话"""
        # Arrange
        novel_id = test_novel.id

        # 创建流程、阶段和会话
        await async_client.post(f"/api/v1/genesis/flows/{novel_id}", headers=auth_headers)
        stage_response = await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}/stages/{GenesisStage.INITIAL_PROMPT.value}",
            json={"config": {}},
            headers=auth_headers
        )
        stage = stage_response.json()
        stage_id = stage["id"]

        # 创建两个会话
        await async_client.post(
            f"/api/v1/genesis/stages/{stage_id}/sessions",
            json={"is_primary": True, "session_kind": "user_interaction"},
            headers=auth_headers
        )
        await async_client.post(
            f"/api/v1/genesis/stages/{stage_id}/sessions",
            json={"is_primary": False, "session_kind": "agent_autonomous"},
            headers=auth_headers
        )

        # Act
        list_response = await async_client.get(
            f"/api/v1/genesis/stages/{stage_id}/sessions",
            headers=auth_headers
        )

        # Assert
        assert list_response.status_code == 200
        sessions = list_response.json()
        assert len(sessions) == 2
        primary_sessions = [s for s in sessions if s["is_primary"]]
        assert len(primary_sessions) == 1

    @pytest.mark.asyncio
    async def test_set_primary_session(self, async_client: AsyncClient, auth_headers, test_novel):
        """测试设置主会话"""
        # Arrange
        novel_id = test_novel.id

        # 创建流程、阶段和两个会话
        await async_client.post(f"/api/v1/genesis/flows/{novel_id}", headers=auth_headers)
        stage_response = await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}/stages/{GenesisStage.INITIAL_PROMPT.value}",
            json={"config": {}},
            headers=auth_headers
        )
        stage = stage_response.json()
        stage_id = stage["id"]

        # 创建第一个会话（主会话）
        session1_response = await async_client.post(
            f"/api/v1/genesis/stages/{stage_id}/sessions",
            json={"is_primary": True, "session_kind": "user_interaction"},
            headers=auth_headers
        )
        session1 = session1_response.json()

        # 创建第二个会话
        session2_response = await async_client.post(
            f"/api/v1/genesis/stages/{stage_id}/sessions",
            json={"is_primary": False, "session_kind": "agent_autonomous"},
            headers=auth_headers
        )
        session2 = session2_response.json()
        session2_id = session2["session_id"]

        # Act - 将第二个会话设为主会话
        set_primary_response = await async_client.put(
            f"/api/v1/genesis/stages/{stage_id}/sessions/{session2_id}/primary",
            headers=auth_headers
        )

        # Assert
        assert set_primary_response.status_code == 200
        updated_association = set_primary_response.json()
        assert updated_association["session_id"] == session2_id
        assert updated_association["is_primary"] is True

    @pytest.mark.asyncio
    async def test_list_genesis_flows_by_status(self, async_client: AsyncClient, auth_headers, test_novel):
        """测试按状态列出Genesis流程"""
        # Arrange
        novel_id = test_novel.id

        # 创建流程
        await async_client.post(f"/api/v1/genesis/flows/{novel_id}", headers=auth_headers)

        # Act
        list_response = await async_client.get(
            f"/api/v1/genesis/flows?status={GenesisStatus.IN_PROGRESS.value}&limit=10&offset=0",
            headers=auth_headers
        )

        # Assert
        assert list_response.status_code == 200
        data = list_response.json()
        assert "flows" in data
        assert "total" in data
        assert "offset" in data
        assert "limit" in data
        assert len(data["flows"]) >= 1
        # 验证返回的流程都是IN_PROGRESS状态
        for flow in data["flows"]:
            assert flow["status"] == GenesisStatus.IN_PROGRESS.value

    @pytest.mark.asyncio
    async def test_genesis_flow_not_found(self, async_client: AsyncClient, auth_headers):
        """测试获取不存在的Genesis流程"""
        # Arrange
        nonexistent_novel_id = "00000000-0000-0000-0000-000000000000"

        # Act
        response = await async_client.get(
            f"/api/v1/genesis/flows/{nonexistent_novel_id}",
            headers=auth_headers
        )

        # Assert
        assert response.status_code == 404
        error = response.json()
        assert "not found" in error["detail"].lower()

    @pytest.mark.asyncio
    async def test_genesis_stage_not_found(self, async_client: AsyncClient, auth_headers):
        """测试获取不存在的Genesis阶段"""
        # Arrange
        nonexistent_stage_id = "00000000-0000-0000-0000-000000000000"

        # Act
        response = await async_client.get(
            f"/api/v1/genesis/stages/{nonexistent_stage_id}",
            headers=auth_headers
        )

        # Assert
        assert response.status_code == 404
        error = response.json()
        assert "not found" in error["detail"].lower()

    @pytest.mark.asyncio
    async def test_version_conflict_on_update(self, async_client: AsyncClient, auth_headers, test_novel):
        """测试更新时的版本冲突"""
        # Arrange
        novel_id = test_novel.id

        # 创建流程
        flow_response = await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}",
            headers=auth_headers
        )
        flow = flow_response.json()

        # Act - 使用错误的版本号更新
        update_data = {
            "current_stage": GenesisStage.WORLDVIEW.value,
            "expected_version": flow["version"] + 10  # 错误的版本号
        }
        update_response = await async_client.put(
            f"/api/v1/genesis/flows/{novel_id}",
            json=update_data,
            headers=auth_headers
        )

        # Assert
        assert update_response.status_code == 409
        error = update_response.json()
        assert "conflict" in error["detail"].lower()