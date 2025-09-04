#!/usr/bin/env node

/**
 * 统一的参数化脚本运行器
 * 用法: pnpm run -- <target> <action> [options]
 * 
 * 例子:
 * - pnpm run -- backend install
 * - pnpm run -- frontend test --e2e
 * - pnpm run -- test all --remote
 * - pnpm run -- infra up
 * - pnpm run -- ssh dev
 */

const { execSync, spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

// 配置
const CONFIG = {
  apps: {
    backend: {
      dir: 'apps/backend',
      packageManager: 'uv',
      commands: {
        install: 'uv sync --all-extras',
        run: 'uv run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000',
        'db:bootstrap': 'uv run is-db-bootstrap',
        lint: 'uv run ruff check src/',
        format: 'uv run ruff format src/',
        typecheck: 'uv run mypy src/ --ignore-missing-imports',
        test: 'uv run pytest tests/unit/ -v',
        'api:simple': './scripts/run-api-gateway-simple.sh',
        'api:local': './scripts/run-api-gateway-local.sh',
        'api:dev': './scripts/run-api-gateway-dev.sh'
      }
    },
    frontend: {
      dir: 'apps/frontend',
      packageManager: 'pnpm',
      commands: {
        install: 'pnpm install',
        run: 'pnpm dev',
        build: 'pnpm build',
        test: 'pnpm test',
        'e2e': 'pnpm test:e2e',
        'e2e:ui': 'pnpm test:e2e:ui',
        'e2e:debug': 'pnpm test:e2e:debug',
        'e2e:auth': 'pnpm test:e2e:auth',
        'e2e:install': 'pnpm test:e2e:install',
        'e2e:report': 'pnpm test:e2e:report'
      }
    }
  },
  
  environments: {
    local: { ip: 'localhost' },
    dev: { ip: '192.168.2.201' },
    test: { ip: '192.168.2.202' }
  },
  
  defaults: {
    TEST_MACHINE_IP: '192.168.2.202',
    SSH_USER: 'zhiyue'
  },
  
  services: {
    maildev: {
      start: 'cd deploy && docker compose --env-file environments/.env.local --profile development up -d maildev',
      stop: 'cd deploy && docker compose --env-file environments/.env.local stop maildev',
      logs: 'cd deploy && docker compose --env-file environments/.env.local logs -f maildev',
      status: 'cd deploy && docker compose --env-file environments/.env.local ps maildev'
    }
  }
};

// 工具函数
function getEnvVar(name, defaultValue) {
  return process.env[name] || CONFIG.defaults[name] || defaultValue;
}

function execCommand(command, options = {}) {
  const { cwd = process.cwd(), stdio = 'inherit' } = options;
  try {
    console.log(`执行: ${command}`);
    if (cwd !== process.cwd()) {
      console.log(`工作目录: ${cwd}`);
    }
    return execSync(command, { cwd, stdio });
  } catch (error) {
    console.error(`命令执行失败: ${command}`);
    process.exit(1);
  }
}

// 主要处理函数
function handleApp(app, action, options = []) {
  const appConfig = CONFIG.apps[app];
  if (!appConfig) {
    console.error(`未知应用: ${app}`);
    process.exit(1);
  }
  
  const command = appConfig.commands[action];
  if (!command) {
    console.error(`应用 ${app} 不支持操作: ${action}`);
    console.log(`可用操作: ${Object.keys(appConfig.commands).join(', ')}`);
    process.exit(1);
  }
  
  const cwd = appConfig.dir;
  const fullCommand = `${command} ${options.join(' ')}`.trim();
  
  execCommand(fullCommand, { cwd });
}

function handleTest(type, options = []) {
  const testMachineIP = getEnvVar('TEST_MACHINE_IP');
  
  // 默认使用本地 Docker 进行测试
  const testCommands = {
    all: `./scripts/test/run-tests.sh --all`,
    unit: `./scripts/test/run-tests.sh --unit`,
    integration: `./scripts/test/run-tests.sh --integration`,
    coverage: `./scripts/test/run-tests.sh --all --coverage`,
    lint: './scripts/test/run-tests.sh --lint'
  };
  
  // 处理远程测试选项
  if (options.includes('--remote')) {
    testCommands.all = `TEST_MACHINE_IP=${testMachineIP} ./scripts/test/run-tests.sh --all --remote`;
    testCommands.unit = `TEST_MACHINE_IP=${testMachineIP} ./scripts/test/run-tests.sh --unit --remote`;
    testCommands.integration = `TEST_MACHINE_IP=${testMachineIP} ./scripts/test/run-tests.sh --integration --remote`;
    testCommands.coverage = `TEST_MACHINE_IP=${testMachineIP} ./scripts/test/run-tests.sh --all --remote --coverage`;
  } else if (options.includes('--docker-host')) {
    // 支持显式指定使用远程 Docker 主机
    testCommands.all = `TEST_MACHINE_IP=${testMachineIP} ./scripts/test/run-tests.sh --all --docker-host`;
    testCommands.unit = `TEST_MACHINE_IP=${testMachineIP} ./scripts/test/run-tests.sh --unit --docker-host`;
    testCommands.integration = `TEST_MACHINE_IP=${testMachineIP} ./scripts/test/run-tests.sh --integration --docker-host`;
    testCommands.coverage = `TEST_MACHINE_IP=${testMachineIP} ./scripts/test/run-tests.sh --all --docker-host --coverage`;
  }
  
  const command = testCommands[type];
  if (!command) {
    console.error(`未知测试类型: ${type}`);
    console.log(`可用类型: ${Object.keys(testCommands).join(', ')}`);
    process.exit(1);
  }
  
  execCommand(`${command} ${options.filter(o => !o.startsWith('--remote') && o !== '--docker-host').join(' ')}`.trim());
}

function handleSSH(env, options = []) {
  const envConfig = CONFIG.environments[env];
  if (!envConfig) {
    console.error(`未知环境: ${env}`);
    console.log(`可用环境: ${Object.keys(CONFIG.environments).join(', ')}`);
    process.exit(1);
  }
  
  const sshUser = getEnvVar('SSH_USER');
  const command = `ssh ${sshUser}@${envConfig.ip}`;
  
  execCommand(command);
}

function handleInfra(action, options = []) {
  const infraCommands = {
    up: './scripts/deploy/infra.sh up',
    down: './scripts/deploy/infra.sh down', 
    deploy: './scripts/deploy/infra.sh',
    status: 'node scripts/ops/check-services-simple.js'
  };
  
  // 处理选项
  if (options.includes('--local')) {
    infraCommands.deploy = './scripts/deploy/infra.sh --local';
  }
  
  const command = infraCommands[action];
  if (!command) {
    console.error(`未知基础设施操作: ${action}`);
    console.log(`可用操作: ${Object.keys(infraCommands).join(', ')}`);
    process.exit(1);
  }
  
  execCommand(`${command} ${options.filter(o => !o.startsWith('--local')).join(' ')}`.trim());
}

function handleService(service, action, options = []) {
  const serviceConfig = CONFIG.services[service];
  if (!serviceConfig) {
    console.error(`未知服务: ${service}`);
    console.log(`可用服务: ${Object.keys(CONFIG.services).join(', ')}`);
    process.exit(1);
  }
  
  const command = serviceConfig[action];
  if (!command) {
    console.error(`服务 ${service} 不支持操作: ${action}`);
    console.log(`可用操作: ${Object.keys(serviceConfig).join(', ')}`);
    process.exit(1);
  }
  
  execCommand(command);
}

function handleAPI(action, options = []) {
  const apiCommands = {
    export: './scripts/tools/hoppscotch-integration.sh',
    'export:dev': './scripts/tools/hoppscotch-integration.sh --url http://192.168.2.201:8000',
    hoppscotch: "./scripts/tools/hoppscotch-integration.sh && echo 'Visit https://hoppscotch.io to import the generated files'"
  };
  
  const command = apiCommands[action];
  if (!command) {
    console.error(`未知API操作: ${action}`);
    console.log(`可用操作: ${Object.keys(apiCommands).join(', ')}`);
    process.exit(1);
  }
  
  execCommand(command);
}

function handleCheck(type, options = []) {
  const checkCommands = {
    services: 'node scripts/ops/check-services-simple.js',
    'services:full': 'node scripts/ops/check-services.js'
  };
  
  // 处理远程选项
  if (options.includes('--remote') || options.includes('--dev')) {
    checkCommands.services = 'node scripts/ops/check-services-simple.js --remote';
    checkCommands['services:full'] = 'node scripts/ops/check-services.js --remote';
  }
  
  const command = checkCommands[type];
  if (!command) {
    console.error(`未知检查类型: ${type}`);
    console.log(`可用类型: ${Object.keys(checkCommands).join(', ')}`);
    process.exit(1);
  }
  
  execCommand(`${command} ${options.filter(o => !o.startsWith('--remote') && o !== '--dev').join(' ')}`.trim());
}

// 帮助信息
function showHelp(target = null) {
  if (target === 'backend' || target === 'frontend') {
    const appConfig = CONFIG.apps[target];
    console.log(`
${target.charAt(0).toUpperCase() + target.slice(1)} 应用操作
用法: pnpm ${target} <action>

可用操作:
${Object.keys(appConfig.commands).map(cmd => `  ${cmd.padEnd(15)} # ${getActionDescription(target, cmd)}`).join('\n')}

示例:
  pnpm ${target} install                # 安装依赖
  pnpm ${target} run                    # 启动开发服务器
  pnpm ${target} lint                   # 代码检查
  pnpm ${target} test                   # 运行测试
`);
    return;
  }
  
  if (target === 'test') {
    console.log(`
测试操作
用法: pnpm test <type> [options]

测试类型:
  all                     # 运行所有测试
  unit                    # 单元测试
  integration             # 集成测试  
  coverage                # 带覆盖率的测试
  lint                    # 代码检查

选项:
  --remote                # 在远程机器上运行测试
  --docker-host           # 使用远程 Docker 主机运行测试

示例:
  pnpm test all                         # 本地 Docker 运行所有测试（默认）
  pnpm test all --remote                # 远程机器运行所有测试
  pnpm test all --docker-host           # 远程 Docker 主机运行测试
  pnpm test unit                        # 本地运行单元测试
`);
    return;
  }
  
  if (target === 'ssh') {
    console.log(`
SSH 连接
用法: pnpm ssh <environment>

环境:
  dev                     # 开发服务器 (192.168.2.201)
  test                    # 测试服务器 (192.168.2.202)

示例:
  pnpm ssh dev                          # 连接开发服务器
  pnpm ssh test                         # 连接测试服务器
`);
    return;
  }
  
  if (target === 'infra') {
    console.log(`
基础设施操作
用法: pnpm infra <action> [options]

操作:
  up                      # 启动基础设施服务
  down                    # 停止基础设施服务
  deploy                  # 部署基础设施
  status                  # 检查服务状态

选项:
  --local                 # 本地部署（仅用于deploy）

示例:
  pnpm infra up                         # 启动服务
  pnpm infra deploy --local             # 本地部署
  pnpm infra status                     # 检查状态
`);
    return;
  }
  
  if (target === 'api') {
    console.log(`
API 工具
用法: pnpm api <action>

操作:
  export                  # 导出API定义
  export:dev              # 导出开发服务器API定义  
  hoppscotch              # 导出并提示访问Hoppscotch

示例:
  pnpm api export                       # 导出本地API
  pnpm api export:dev                   # 导出开发环境API
  pnpm api hoppscotch                   # 导出并显示导入提示
`);
    return;
  }
  
  if (target === 'service') {
    console.log(`
服务管理
用法: pnpm service <service> <action>

服务:
  maildev                 # 邮件开发服务

操作:
  start                   # 启动服务
  stop                    # 停止服务  
  logs                    # 查看日志
  status                  # 检查状态

示例:
  pnpm maildev start                    # 启动邮件服务
  pnpm maildev logs                     # 查看邮件服务日志
`);
    return;
  }
  
  if (target === 'check') {
    console.log(`
服务检查
用法: pnpm check <type> [options]

检查类型:
  services                # 快速服务健康检查
  services:full           # 完整服务健康检查

选项:
  --remote                # 检查远程服务器服务 (192.168.2.201)
  --dev                   # 检查开发服务器服务 (别名 --remote)

示例:
  pnpm check services                   # 检查本地服务（默认）
  pnpm check services --remote          # 检查远程开发服务器服务
  pnpm check services:full              # 完整检查本地服务
  pnpm check services:full --remote     # 完整检查远程服务器服务
`);
    return;
  }
  
  console.log(`
统一脚本运行器 - 参数化命令系统

## 快速命令 (推荐):
  pnpm backend <action>                 # 后端操作
  pnpm frontend <action>                # 前端操作  
  pnpm test <type>                      # 测试操作
  pnpm ssh <env>                        # SSH连接
  pnpm infra <action>                   # 基础设施
  pnpm check <type>                     # 服务检查
  pnpm api <action>                     # API工具

## 完整用法:
  pnpm run -- <target> <action> [options]

目标 (target):
  backend          后端应用操作 (Python/FastAPI)
  frontend         前端应用操作 (React/TypeScript)  
  test             测试操作 (单元/集成/E2E)
  ssh              SSH连接 (dev/test环境)
  infra            基础设施操作 (Docker/部署)
  check            服务健康检查 (本地/远程)
  service          服务管理 (maildev等)
  api              API工具 (导出/测试)

## 示例命令:
  pnpm backend install                  # 安装后端依赖
  pnpm frontend run                     # 启动前端开发服务器
  pnpm test all --remote                # 远程运行所有测试
  pnpm ssh dev                          # 连接开发服务器  
  pnpm infra up                         # 启动基础设施
  pnpm check services                   # 检查本地服务健康状态
  pnpm check services --remote          # 检查远程服务健康状态
  pnpm maildev start                    # 启动邮件服务
  pnpm api export                       # 导出API定义

## 获取特定帮助:
  pnpm <target> --help                  # 获取目标相关帮助

## 优势:
  - 减少86%重复代码 (从88个脚本 -> 12个核心脚本)
  - 统一环境变量管理
  - 参数化配置，易于维护
  - 保持向后兼容性
`);
}

function getActionDescription(app, action) {
  const descriptions = {
    backend: {
      install: '安装Python依赖',
      run: '启动API网关服务器',
      'db:bootstrap': '初始化PostgreSQL/Neo4j/Milvus/Redis（一次性）',
      lint: '运行Ruff代码检查',
      format: '格式化Python代码',
      typecheck: '运行MyPy类型检查', 
      test: '运行单元测试',
      'api:simple': '运行简单API网关',
      'api:local': '运行本地API网关',
      'api:dev': '运行开发API网关'
    },
    frontend: {
      install: '安装Node.js依赖',
      run: '启动Vite开发服务器',
      build: '构建生产版本',
      test: '运行Jest测试',
      'e2e': '运行E2E测试',
      'e2e:ui': '运行E2E测试(UI模式)',
      'e2e:debug': '调试E2E测试',
      'e2e:auth': '运行认证E2E测试',
      'e2e:install': '安装E2E测试依赖',
      'e2e:report': '生成E2E测试报告'
    }
  };
  
  return descriptions[app]?.[action] || action;
}

// 主入口
function main() {
  const args = process.argv.slice(2);
  
  if (args.length === 0 || args.includes('--help') || args.includes('-h')) {
    showHelp();
    return;
  }
  
  const [target, action, ...options] = args;
  
  // 处理帮助请求
  if (action === '--help' || action === '-h') {
    showHelp(target);
    return;
  }
  
  switch (target) {
    case 'backend':
    case 'frontend':
      if (!action) {
        showHelp(target);
        return;
      }
      handleApp(target, action, options);
      break;
      
    case 'test':
      if (!action) {
        showHelp(target);
        return;
      }
      handleTest(action, options);
      break;
      
    case 'ssh':
      if (!action) {
        showHelp(target);  
        return;
      }
      handleSSH(action, options);
      break;
      
    case 'infra':
      if (!action) {
        showHelp(target);
        return;
      }
      handleInfra(action, options);
      break;
      
    case 'service':
      if (!action) {
        showHelp(target);
        return;
      }
      handleService(action, options[0], options.slice(1));
      break;
      
    case 'api':
      if (!action) {
        showHelp(target);
        return;
      }
      handleAPI(action, options);
      break;
      
    case 'check':
      if (!action) {
        showHelp(target);
        return;
      }
      handleCheck(action, options);
      break;
      
    default:
      console.error(`未知目标: ${target}`);
      showHelp();
      process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = { CONFIG, main };
