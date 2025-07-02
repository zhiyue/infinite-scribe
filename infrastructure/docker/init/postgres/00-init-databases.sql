-- 确保必要的扩展已安装
-- pgcrypto扩展用于gen_random_uuid()函数，在所有后续脚本中都会用到
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Create Prefect database
CREATE DATABASE prefect WITH ENCODING='UTF-8' LC_COLLATE='en_US.utf8' LC_CTYPE='en_US.utf8';

-- Grant all privileges on prefect database to the postgres user
GRANT ALL PRIVILEGES ON DATABASE prefect TO postgres;

-- 为prefect数据库也安装必要的扩展
\c prefect;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 切换回默认数据库
\c infinite_scribe;