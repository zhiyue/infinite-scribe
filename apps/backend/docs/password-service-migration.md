# 密码服务迁移记录

## 迁移日期
2025-01-10

## 迁移内容
从 passlib + bcrypt 组合迁移到直接使用 bcrypt

## 迁移原因
1. passlib 1.7.4 与 bcrypt 4.x 版本不兼容
2. passlib 项目已经很久没有更新（最后更新是 2020 年）
3. 直接使用 bcrypt 更简单，减少依赖层级
4. bcrypt 4.x 提供更好的性能和安全性

## 主要变化

### 1. 依赖更新
```diff
- "passlib[bcrypt]>=1.7.4",
- "bcrypt>=3.2.0,<4.0.0",
+ "bcrypt>=4.0.0,<5.0.0",
```

### 2. 代码更改
文件：`src/common/services/password_service.py`

**之前（使用 passlib）：**
```python
from passlib.context import CryptContext

self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
return self.pwd_context.hash(password)
return self.pwd_context.verify(plain_password, hashed_password)
```

**之后（直接使用 bcrypt）：**
```python
import bcrypt

# 哈希密码
password_bytes = password.encode('utf-8')
salt = bcrypt.gensalt(rounds=self.rounds)
hashed = bcrypt.hashpw(password_bytes, salt)
return hashed.decode('utf-8')

# 验证密码
password_bytes = plain_password.encode('utf-8')
hashed_bytes = hashed_password.encode('utf-8')
return bcrypt.checkpw(password_bytes, hashed_bytes)
```

## 功能验证
✅ 密码哈希功能正常
✅ 密码验证功能正常
✅ 密码强度验证功能正常
✅ API 服务启动正常
✅ 数据库迁移工具（alembic）正常

## 注意事项
1. bcrypt 生成的哈希值格式与之前兼容，不需要重新哈希现有密码
2. 默认使用 12 轮（rounds）加密，可以根据需要调整
3. 所有密码操作都需要在字节和字符串之间转换

## 性能考虑
- bcrypt 4.x 相比 3.x 版本有性能提升
- 直接使用 bcrypt 减少了一层抽象，性能略有提升
- 12 轮加密在安全性和性能之间取得平衡