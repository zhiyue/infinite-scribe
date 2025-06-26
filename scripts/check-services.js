#!/usr/bin/env node

const http = require('http');
const https = require('https');
const { Client } = require('pg');
const redis = require('redis');
const neo4j = require('neo4j-driver');
const { Kafka } = require('kafkajs');
const { MilvusClient } = require('@zilliz/milvus2-sdk-node');
const { S3Client, ListBucketsCommand } = require('@aws-sdk/client-s3');

// Configuration
const DEV_SERVER = process.env.DEV_SERVER || '192.168.2.201';
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
        host: DEV_SERVER,
        port: 5432,
        user: process.env.POSTGRES_USER || 'postgres',
        password: process.env.POSTGRES_PASSWORD || 'postgres',
        database: 'postgres',
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
          host: DEV_SERVER,
          port: 6379,
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
      const driver = neo4j.driver(
        `bolt://${DEV_SERVER}:7687`,
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
      return checkHttp(`http://${DEV_SERVER}:7474`, 'Neo4j Browser UI');
    }
  },
  {
    name: 'Kafka',
    port: 9092,
    check: async () => {
      const kafka = new Kafka({
        clientId: 'check-services',
        brokers: [`${DEV_SERVER}:9092`],
        connectionTimeout: CHECKS_TIMEOUT,
        requestTimeout: CHECKS_TIMEOUT
      });
      
      const admin = kafka.admin();
      try {
        await admin.connect();
        const topics = await admin.listTopics();
        await admin.disconnect();
        return { success: true, info: `Connected, ${topics.length} topics found` };
      } catch (error) {
        return { success: false, error: error.message };
      }
    }
  },
  {
    name: 'Milvus',
    port: 19530,
    check: async () => {
      const milvusClient = new MilvusClient({
        address: `${DEV_SERVER}:19530`,
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
      const s3Client = new S3Client({
        endpoint: `http://${DEV_SERVER}:9000`,
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
      return checkHttp(`http://${DEV_SERVER}:9001`, 'MinIO Console UI');
    }
  },
  {
    name: 'Prefect API',
    port: 4200,
    check: async () => {
      try {
        const healthCheck = await checkHttp(`http://${DEV_SERVER}:4200/api/health`);
        if (!healthCheck.success) return healthCheck;
        
        // Additional API check
        const response = await fetch(`http://${DEV_SERVER}:4200/api/version`);
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
      return checkHttp(`http://${DEV_SERVER}:4200`, 'Prefect Web UI');
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
  console.log(`${colors.blue}Development Server: ${DEV_SERVER}${colors.reset}`);
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
    console.log(`ssh ${process.env.USER || 'zhiyue'}@${DEV_SERVER} "cd ~/workspace/mvp/infinite-scribe && docker compose up -d"`);
  }
  
  // Exit code based on health
  process.exit(healthyCount === services.length ? 0 : 1);
}

// Run if called directly
if (require.main === module) {
  main().catch(console.error);
}

module.exports = { checkServices: main };