"""
事件溯源模型测试 - 已分割为更小的文件

此文件已分割为以下更小的测试文件以满足400行限制：
- test_event_models.py: 事件和命令相关模型测试
- test_task_flow_models.py: 任务和流程相关模型测试

请使用这些分割后的文件进行测试。
"""

# 导入分割后的测试模块以保持向后兼容性
from .test_event_models import *
from .test_task_flow_models import *

if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])