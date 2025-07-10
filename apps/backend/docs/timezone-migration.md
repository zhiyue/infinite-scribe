# 时区处理迁移记录

## 迁移日期
2025-01-10

## 迁移概述
将数据库时间字段从 `TIMESTAMP` 迁移到 `TIMESTAMP WITH TIME ZONE (timestamptz)`，并更新相关代码以支持时区感知的 datetime 对象。

## 主要变化

### 1. 数据库模式更新
已通过 Alembic 迁移 `e63af3b9a311` 将以下表的时间字段更新为 `timestamptz`：

- **users 表**：6 个时间字段
- **sessions 表**：6 个时间字段
- **email_verifications 表**：4 个时间字段

### 2. datetime_utils.py 更新

#### 更新的函数：
- `utc_now()` - 现在返回带 UTC 时区的 datetime
- `from_timestamp_utc()` - 返回带时区的 datetime

#### 新增的函数：
- `ensure_utc()` - 确保 datetime 对象带有 UTC 时区
- `to_timestamp()` - 将 datetime 转换为 Unix 时间戳
- `parse_iso_datetime()` - 解析 ISO 8601 时间字符串
- `format_iso_datetime()` - 格式化为 ISO 8601 字符串

### 3. 模型更新

更新了以下模型中的 `datetime.utcnow()` 使用：

- **user.py**
  - `password_changed_at` 默认值
  - `is_locked` 属性方法
  
- **session.py**
  - `last_accessed_at` 默认值
  - `is_access_token_expired` 属性方法
  - `is_refresh_token_expired` 属性方法
  - `revoke()` 方法

## 最佳实践

### 1. 始终使用时区感知的 datetime
```python
# 推荐
from src.common.utils.datetime_utils import utc_now
now = utc_now()  # 返回带 UTC 时区的 datetime

# 不推荐
from datetime import datetime
now = datetime.utcnow()  # 返回无时区的 datetime
```

### 2. 处理用户输入的时间
```python
from src.common.utils.datetime_utils import parse_iso_datetime

# 解析 ISO 8601 格式
dt = parse_iso_datetime("2025-01-11T12:00:00Z")
# 或
dt = parse_iso_datetime("2025-01-11T20:00:00+08:00")
```

### 3. 确保时间总是 UTC
```python
from src.common.utils.datetime_utils import ensure_utc

# 将任意时区的时间转换为 UTC
utc_time = ensure_utc(some_datetime)
```

### 4. 在 API 响应中格式化时间
```python
from src.common.utils.datetime_utils import format_iso_datetime

# 格式化为 ISO 8601
iso_string = format_iso_datetime(dt)
# 输出: "2025-01-11T12:00:00+00:00"
```

## 优势

1. **时区安全**：所有时间都明确带有时区信息，避免混淆
2. **国际化支持**：正确处理不同时区的用户
3. **PostgreSQL 最佳实践**：使用 `timestamptz` 是 PostgreSQL 推荐的方式
4. **标准兼容**：ISO 8601 格式便于前后端交互

## 注意事项

1. 现有数据不会丢失，迁移只改变列类型
2. 所有时间在数据库中以 UTC 存储
3. 客户端显示时可以根据用户时区转换
4. 新增的时区感知功能向后兼容

## 验证

✅ 数据库迁移成功应用
✅ 时区工具函数测试通过
✅ API 服务正常启动
✅ 密码服务功能正常