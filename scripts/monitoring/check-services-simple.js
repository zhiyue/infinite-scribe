#!/usr/bin/env node

const http = require('http');
const net = require('net');
const { execSync } = require('child_process');

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

// Service definitions with port checks
const services = [
  { name: 'PostgreSQL', port: 5432, type: 'tcp' },
  { name: 'Redis', port: 6379, type: 'tcp' },
  { name: 'Neo4j (Bolt)', port: 7687, type: 'tcp' },
  { name: 'Neo4j Browser', port: 7474, type: 'http', path: '/' },
  { name: 'Kafka', port: 9092, type: 'tcp' },
  { name: 'Milvus', port: 19530, type: 'tcp' },
  { name: 'Milvus Metrics', port: 9091, type: 'http', path: '/metrics' },
  { name: 'MinIO API', port: 9000, type: 'http', path: '/minio/health/live' },
  { name: 'MinIO Console', port: 9001, type: 'http', path: '/' },
  { name: 'Prefect API', port: 4200, type: 'http', path: '/api/health' },
  { name: 'Prefect UI', port: 4200, type: 'http', path: '/' }
];

// Check TCP port
function checkTcpPort(host, port, timeout = CHECKS_TIMEOUT) {
  return new Promise((resolve) => {
    const socket = new net.Socket();
    
    socket.setTimeout(timeout);
    
    socket.on('connect', () => {
      socket.destroy();
      resolve({ success: true, info: 'Port is open' });
    });
    
    socket.on('timeout', () => {
      socket.destroy();
      resolve({ success: false, error: 'Connection timeout' });
    });
    
    socket.on('error', (err) => {
      resolve({ success: false, error: err.message });
    });
    
    socket.connect(port, host);
  });
}

// Check HTTP endpoint
function checkHttp(host, port, path = '/', timeout = CHECKS_TIMEOUT) {
  return new Promise((resolve) => {
    const options = {
      hostname: host,
      port: port,
      path: path,
      method: 'GET',
      timeout: timeout
    };
    
    const req = http.request(options, (res) => {
      if (res.statusCode >= 200 && res.statusCode < 400) {
        resolve({ 
          success: true, 
          info: `HTTP ${res.statusCode}` 
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
        error: 'Request timeout' 
      });
    });
    
    req.end();
  });
}

// Check Docker containers on remote server
async function checkDockerContainers() {
  console.log(`\n${colors.blue}Docker Container Status:${colors.reset}`);
  console.log(`${colors.blue}${'='.repeat(50)}${colors.reset}\n`);
  
  try {
    const cmd = `ssh zhiyue@${DEV_SERVER} "cd ~/workspace/mvp/infinite-scribe && docker compose ps --format 'table {{.Names}}\\t{{.Status}}'"`;
    const output = execSync(cmd, { encoding: 'utf8' });
    
    const lines = output.trim().split('\n');
    lines.forEach((line, index) => {
      if (index === 0) {
        console.log(`${colors.bold}${line}${colors.reset}`);
      } else if (line.includes('(healthy)')) {
        console.log(`${colors.green}${line}${colors.reset}`);
      } else if (line.includes('(unhealthy)')) {
        console.log(`${colors.red}${line}${colors.reset}`);
      } else {
        console.log(line);
      }
    });
  } catch (error) {
    console.log(`${colors.red}Failed to get Docker container status${colors.reset}`);
    console.log(`Error: ${error.message}`);
  }
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
    process.stdout.write(`Checking ${service.name}...`.padEnd(35));
    
    try {
      let result;
      if (service.type === 'tcp') {
        result = await checkTcpPort(DEV_SERVER, service.port);
      } else if (service.type === 'http') {
        result = await checkHttp(DEV_SERVER, service.port, service.path);
      }
      
      results.push({ ...service, ...result });
      
      if (result.success) {
        healthyCount++;
        console.log(`${colors.green}✓ OK${colors.reset} - ${result.info}`);
      } else {
        console.log(`${colors.red}✗ FAIL${colors.reset} - ${result.error}`);
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
  
  // Check Docker containers
  await checkDockerContainers();
  
  // Service URLs
  console.log(`\n${colors.blue}Service URLs:${colors.reset}`);
  console.log(`${colors.blue}${'='.repeat(50)}${colors.reset}\n`);
  console.log(`Neo4j Browser:   http://${DEV_SERVER}:7474`);
  console.log(`MinIO Console:   http://${DEV_SERVER}:9001`);
  console.log(`Prefect UI:      http://${DEV_SERVER}:4200`);
  console.log(`Prefect API:     http://${DEV_SERVER}:4200/api`);
  console.log(`Milvus Metrics:  http://${DEV_SERVER}:9091/metrics`);
  
  // Docker compose hint
  if (healthyCount < services.length) {
    console.log(`\n${colors.yellow}Hint: To start all services, run:${colors.reset}`);
    console.log(`ssh zhiyue@${DEV_SERVER} "cd ~/workspace/mvp/infinite-scribe && docker compose up -d"`);
    console.log(`\n${colors.yellow}To check logs for failed services:${colors.reset}`);
    console.log(`ssh zhiyue@${DEV_SERVER} "cd ~/workspace/mvp/infinite-scribe && docker compose logs [service-name]"`);
  } else {
    console.log(`\n${colors.green}All services are running! 🎉${colors.reset}`);
  }
  
  // Exit code based on health
  process.exit(healthyCount === services.length ? 0 : 1);
}

// Run if called directly
if (require.main === module) {
  main().catch(console.error);
}

module.exports = { checkServices: main };