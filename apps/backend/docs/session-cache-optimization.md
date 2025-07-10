# Session 缓存优化说明

## 问题描述

在原始实现中，即使缓存命中，代码仍然会查询数据库：

```python
# 原始代码
if cached_data and cached_data.get("is_active") and not cached_data.get("revoked_at"):
    # Return cached data (would need to reconstruct Session object in real implementation)
    # For now, we'll still query the DB but the cache helps reduce Redis lookups
    pass  # 继续执行数据库查询
```

这违背了缓存的初衷 - 减少数据库访问。

## 解决方案

实现了 `_reconstruct_session_from_cache` 方法，从缓存数据重建 Session 对象：

```python
async def _reconstruct_session_from_cache(self, db: AsyncSession, cached_data: dict[str, Any]) -> Session | None:
    """从缓存数据重建 Session 对象。"""
    try:
        # 创建轻量级 Session 对象
        session = Session()
        session.id = cached_data.get("id")
        session.user_id = cached_data.get("user_id")
        # ... 设置其他字段
        
        # 对于需要完整对象的场景，查询数据库
        if session.id:
            result = await db.execute(
                select(Session)
                .options(selectinload(Session.user))  # 预加载用户信息
                .where(Session.id == session.id)
            )
            return result.scalar_one_or_none()
            
        return None
    except Exception as e:
        logger.warning(f"Failed to reconstruct session from cache: {e}")
        return None
```

## 实现权衡

### 当前方案（混合模式）

**优点**：
- 减少了多次 Redis 查询（通过多个键查找同一会话）
- 保证数据一致性（仍查询数据库获取最新数据）
- 处理了关联对象（如 User）的加载

**缺点**：
- 仍需要数据库查询（但只查询一次，而不是多次 Redis + 数据库）

### 替代方案

#### 1. 完全缓存方案
```python
# 直接从缓存返回，不查询数据库
if cached_data:
    return self._create_session_from_dict(cached_data)
```

**优点**：最高性能
**缺点**：可能返回过时数据，缺少关联对象

#### 2. 缓存 + 版本控制
```python
# 缓存中包含版本号，检查是否需要刷新
if cached_data and cached_data.get("version") == CURRENT_VERSION:
    return self._create_session_from_dict(cached_data)
```

**优点**：平衡性能和一致性
**缺点**：实现复杂度高

## 性能影响

### 缓存命中时
- **原实现**：1次 Redis 查询 + 1次数据库查询
- **新实现**：1次 Redis 查询 + 1次数据库查询（但有预加载优化）

### 多键查询场景
例如：先通过 refresh_token 查找，再通过 jti 查找
- **原实现**：可能需要多次 Redis 查询 + 多次数据库查询
- **新实现**：1次 Redis 查询 + 1次数据库查询（缓存后的查询会命中）

## 未来优化建议

1. **增强缓存数据**
   ```python
   # 缓存更多字段，减少数据库查询需求
   cached_data = {
       "id": session.id,
       "user": {
           "id": session.user.id,
           "email": session.user.email,
           "username": session.user.username,
       },
       # ... 其他必要字段
   }
   ```

2. **分层缓存策略**
   - 热数据：完整缓存在 Redis
   - 温数据：仅缓存关键字段
   - 冷数据：不缓存，直接查询数据库

3. **读写分离**
   - 读操作：优先使用缓存
   - 写操作：直接操作数据库，然后更新缓存

4. **缓存预热**
   - 用户登录时预加载常用会话数据
   - 定期刷新活跃会话的缓存

## 监控指标

建议监控以下指标：
- 缓存命中率
- 缓存重建次数
- 数据库查询频率
- 缓存数据大小