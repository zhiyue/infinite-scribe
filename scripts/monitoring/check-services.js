#!/usr/bin/env node

// 加载环境变量
require('dotenv').config();

const http = require('http');
const https = require('https');
const { Client } = require('pg');
const redis = require('redis');
const neo4j = require('neo4j-driver');
const { Kafka } = require('kafkajs');
const { MilvusClient } = require('@zilliz/milvus2-sdk-node');
const { S3Client, ListBucketsCommand } = require('@aws-sdk/client-s3');

// Configuration
// 默认的开发服务器地址，各服务可以通过自己的 HOST 环境变量覆盖
const DEFAULT_HOST = process.env.INFRASTRUCTURE_HOST || '192.168.2.201';
const CHECKS_TIMEOUT = 5000; // 5 seconds timeout for each check

// Color codes for terminal output
const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[36m',
  bold: '\x1b[1m'
};

// Service definitions
const services = [
  {
    name: 'PostgreSQL',
    port: 5432,
    check: async () => {
      const client = new Client({
        host: process.env.POSTGRES_HOST || DEFAULT_HOST,
        port: process.env.POSTGRES_PORT || 5432,
        user: process.env.POSTGRES_USER || 'postgres',
        password: process.env.POSTGRES_PASSWORD || 'postgres',
        database: process.env.POSTGRES_DB || 'postgres',
        connectionTimeoutMillis: CHECKS_TIMEOUT
      });

      try {
        await client.connect();
        const res = await client.query('SELECT NOW()');
        await client.end();
        return { success: true, info: `Connected, server time: ${res.rows[0].now}` };
      } catch (error) {
        return { success: false, error: error.message };
      }
    }
  },
  {
    name: 'Redis',
    port: 6379,
    check: async () => {
      const client = redis.createClient({
        socket: {
          host: process.env.REDIS_HOST || DEFAULT_HOST,
          port: process.env.REDIS_PORT || 6379,
          connectTimeout: CHECKS_TIMEOUT
        },
        password: process.env.REDIS_PASSWORD || 'redis'
      });

      try {
        await client.connect();
        await client.ping();
        const info = await client.info('server');
        await client.quit();
        const version = info.match(/redis_version:([^\r\n]+)/)?.[1];
        return { success: true, info: `Connected, version: ${version}` };
      } catch (error) {
        return { success: false, error: error.message };
      }
    }
  },
  {
    name: 'Neo4j',
    port: 7687,
    check: async () => {
      const host = process.env.NEO4J_HOST || DEFAULT_HOST;
      const port = process.env.NEO4J_PORT || 7687;
      const driver = neo4j.driver(
        `bolt://${host}:${port}`,
        neo4j.auth.basic(
          process.env.NEO4J_USER || 'neo4j',
          process.env.NEO4J_PASSWORD || 'neo4j'
        )
      );

      try {
        const session = driver.session();
        const result = await session.run('RETURN 1 as num');
        await session.close();
        await driver.close();
        return { success: true, info: 'Connected, Bolt protocol working' };
      } catch (error) {
        await driver.close();
        return { success: false, error: error.message };
      }
    }
  },
  {
    name: 'Neo4j Browser',
    port: 7474,
    check: async () => {
      const host = process.env.NEO4J_HOST || DEFAULT_HOST;
      return checkHttp(`http://${host}:7474`, 'Neo4j Browser UI');
    }
  },
  {
    name: 'Kafka',
    port: 9092,
    check: async () => {
      const host = process.env.KAFKA_HOST || DEFAULT_HOST;
      const port = process.env.KAFKA_PORT || 9092;
      
      // 临时禁用警告（kafkajs 已知问题）
      const originalEmit = process.emit;
      process.emit = function (name, warning) {
        if (name === 'warning' && warning.name === 'TimeoutNegativeWarning') {
          return false;
        }
        return originalEmit.apply(process, arguments);
      };
      
      const kafka = new Kafka({
        clientId: 'check-services',
        brokers: [`${host}:${port}`],
        connectionTimeout: CHECKS_TIMEOUT,
        requestTimeout: CHECKS_TIMEOUT,
        retry: {
          initialRetryTime: 100,
          retries: 3
        }
      });

      const admin = kafka.admin();
      try {
        await admin.connect();
        const topics = await admin.listTopics();
        await admin.disconnect();
        
        // 恢复原始的 emit 函数
        process.emit = originalEmit;
        
        return { success: true, info: `Connected, ${topics.length} topics found` };
      } catch (error) {
        // 恢复原始的 emit 函数
        process.emit = originalEmit;
        
        return { success: false, error: error.message };
      }
    }
  },
  {
    name: 'Milvus',
    port: 19530,
    check: async () => {
      const host = process.env.MILVUS_HOST || DEFAULT_HOST;
      const port = process.env.MILVUS_PORT || 19530;
      const milvusClient = new MilvusClient({
        address: `${host}:${port}`,
        timeout: CHECKS_TIMEOUT
      });

      try {
        const health = await milvusClient.checkHealth();
        return { success: health.isHealthy, info: 'Connected, server is healthy' };
      } catch (error) {
        return { success: false, error: error.message };
      }
    }
  },
  {
    name: 'MinIO',
    port: 9000,
    check: async () => {
      const host = process.env.MINIO_HOST || DEFAULT_HOST;
      const port = process.env.MINIO_PORT || 9000;
      const s3Client = new S3Client({
        endpoint: `http://${host}:${port}`,
        region: 'us-east-1',
        credentials: {
          accessKeyId: process.env.MINIO_ACCESS_KEY || 'minioadmin',
          secretAccessKey: process.env.MINIO_SECRET_KEY || 'minioadmin'
        },
        forcePathStyle: true
      });

      try {
        const command = new ListBucketsCommand({});
        const response = await s3Client.send(command);
        return {
          success: true,
          info: `Connected, ${response.Buckets?.length || 0} buckets found`
        };
      } catch (error) {
        return { success: false, error: error.message };
      }
    }
  },
  {
    name: 'MinIO Console',
    port: 9001,
    check: async () => {
      const host = process.env.MINIO_HOST || DEFAULT_HOST;
      return checkHttp(`http://${host}:9001`, 'MinIO Console UI');
    }
  },
  {
    name: 'Prefect API',
    port: 4200,
    check: async () => {
      try {
        const host = process.env.PREFECT_HOST || DEFAULT_HOST;
        const port = process.env.PREFECT_PORT || 4200;
        const healthCheck = await checkHttp(`http://${host}:${port}/api/health`);
        if (!healthCheck.success) return healthCheck;

        // Additional API check
        const response = await fetch(`http://${host}:${port}/api/version`);
        const data = await response.json();
        return {
          success: true,
          info: `API healthy, version: ${data.version || 'unknown'}`
        };
      } catch (error) {
        return { success: false, error: error.message };
      }
    }
  },
  {
    name: 'Prefect UI',
    port: 4200,
    check: async () => {
      const host = process.env.PREFECT_HOST || DEFAULT_HOST;
      const port = process.env.PREFECT_PORT || 4200;
      return checkHttp(`http://${host}:${port}`, 'Prefect Web UI');
    }
  },
  {
    name: 'API Gateway',
    port: 8000,
    check: async () => {
      try {
        const host = process.env.API_GATEWAY_HOST || DEFAULT_HOST;
        const port = process.env.API_GATEWAY_PORT || 8000;
        const response = await fetch(`http://${host}:${port}/health`);
        const data = await response.json();
        if (response.ok && data.status === 'ok') {
          return {
            success: true,
            info: 'API Gateway healthy, all database connections OK'
          };
        } else {
          return {
            success: false,
            error: `Health check failed: ${JSON.stringify(data)}`
          };
        }
      } catch (error) {
        return { success: false, error: error.message };
      }
    }
  }
];

// Helper function to check HTTP endpoints
async function checkHttp(url, serviceName = '') {
  return new Promise((resolve) => {
    const client = url.startsWith('https') ? https : http;

    const req = client.get(url, { timeout: CHECKS_TIMEOUT }, (res) => {
      if (res.statusCode >= 200 && res.statusCode < 400) {
        resolve({
          success: true,
          info: `${serviceName} accessible, status: ${res.statusCode}`
        });
      } else {
        resolve({
          success: false,
          error: `HTTP ${res.statusCode}`
        });
      }
    });

    req.on('error', (err) => {
      resolve({
        success: false,
        error: err.message
      });
    });

    req.on('timeout', () => {
      req.destroy();
      resolve({
        success: false,
        error: 'Connection timeout'
      });
    });
  });
}

// Main execution
async function main() {
  console.log(`${colors.bold}${colors.blue}InfiniteScribe Service Health Check${colors.reset}`);
  console.log(`${colors.blue}Default Host: ${DEFAULT_HOST}${colors.reset}`);
  console.log(`${colors.blue}${'='.repeat(50)}${colors.reset}\n`);

  const results = [];
  let healthyCount = 0;

  // Check each service
  for (const service of services) {
    process.stdout.write(`Checking ${service.name}...`.padEnd(30));

    try {
      const result = await service.check();
      results.push({ ...service, ...result });

      if (result.success) {
        healthyCount++;
        console.log(`${colors.green}✓ HEALTHY${colors.reset} - ${result.info}`);
      } else {
        console.log(`${colors.red}✗ FAILED${colors.reset} - ${result.error}`);
      }
    } catch (error) {
      results.push({ ...service, success: false, error: error.message });
      console.log(`${colors.red}✗ ERROR${colors.reset} - ${error.message}`);
    }
  }

  // Summary
  console.log(`\n${colors.blue}${'='.repeat(50)}${colors.reset}`);
  console.log(`${colors.bold}Summary:${colors.reset}`);
  console.log(`Total services: ${services.length}`);
  console.log(`${colors.green}Healthy: ${healthyCount}${colors.reset}`);
  console.log(`${colors.red}Failed: ${services.length - healthyCount}${colors.reset}`);

  // Docker compose hint
  if (healthyCount < services.length) {
    console.log(`\n${colors.yellow}Hint: To start all services, run:${colors.reset}`);
    console.log(`ssh ${process.env.USER || 'zhiyue'}@${DEFAULT_HOST} "cd ~/workspace/mvp/infinite-scribe && docker compose up -d"`);
  }

  // Exit code based on health
  process.exit(healthyCount === services.length ? 0 : 1);
}

// Run if called directly
if (require.main === module) {
  main().catch(console.error);
}

module.exports = { checkServices: main };
