-- ================================================
-- 00-init-databases.sql
-- 数据库和扩展初始化脚本
-- ================================================
--
-- 此脚本负责：
-- 1. 安装必要的PostgreSQL扩展
-- 2. 创建Prefect工作流引擎所需的数据库
-- 3. 为各数据库配置必要的扩展
--

-- 设置搜索路径，避免多schema环境问题
SET search_path TO public;
-- 依赖关系：无（第一个执行的脚本）
-- ================================================

-- 确保必要的扩展已安装
-- pgcrypto扩展用于gen_random_uuid()函数，在所有后续脚本中都会用到
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- btree_gin扩展用于优化JSONB字段的索引性能
CREATE EXTENSION IF NOT EXISTS btree_gin;

-- pg_stat_statements扩展用于性能监控和查询分析
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Create Prefect database
-- Prefect是我们使用的工作流引擎，需要独立的数据库
CREATE DATABASE prefect WITH 
    ENCODING='UTF-8' 
    LC_COLLATE='en_US.utf8' 
    LC_CTYPE='en_US.utf8'
    TEMPLATE=template0;

-- Grant all privileges on prefect database to the postgres user
GRANT ALL PRIVILEGES ON DATABASE prefect TO postgres;

-- 为prefect数据库也安装必要的扩展
\c prefect;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS btree_gin;

-- 切换回主数据库infinite_scribe
\c infinite_scribe;

-- 验证扩展安装
DO $$
BEGIN
    -- 检查关键扩展是否已安装
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pgcrypto') THEN
        RAISE EXCEPTION 'pgcrypto扩展安装失败，后续脚本将无法执行';
    END IF;
    
    RAISE NOTICE '数据库初始化完成：';
    RAISE NOTICE '- infinite_scribe: 主应用数据库';
    RAISE NOTICE '- prefect: 工作流引擎数据库';
    RAISE NOTICE '- 已安装扩展: pgcrypto, btree_gin, pg_stat_statements';
END $$;