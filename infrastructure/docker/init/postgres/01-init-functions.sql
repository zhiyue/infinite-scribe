-- ================================================
-- 01-init-functions.sql
-- 基础函数定义脚本
-- ================================================
--
-- 此脚本负责：
-- 1. 创建自动更新时间戳的触发器函数
-- 2. 创建其他通用的数据库函数
--

-- 设置搜索路径，避免多schema环境问题
SET search_path TO public;

-- 依赖关系：00-init-databases.sql（需要pgcrypto扩展）
-- ================================================

-- 自动更新 'updated_at' 字段的函数
-- 这个函数将被用于所有有updated_at字段的表，以确保数据修改时自动更新时间戳
CREATE OR REPLACE FUNCTION trigger_set_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION trigger_set_timestamp() IS '自动更新触发器函数，用于在行更新时自动设置updated_at字段为当前时间';

-- 验证函数创建
DO $$
BEGIN
    -- 检查关键函数是否已创建
    IF NOT EXISTS (
        SELECT 1 FROM pg_proc 
        WHERE proname = 'trigger_set_timestamp' 
        AND pg_get_function_result(oid) = 'trigger'
    ) THEN
        RAISE EXCEPTION 'trigger_set_timestamp函数创建失败';
    END IF;
    
    RAISE NOTICE '基础函数创建完成：';
    RAISE NOTICE '- trigger_set_timestamp(): 自动更新时间戳触发器函数';
END $$;