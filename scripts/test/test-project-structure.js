#!/usr/bin/env node

/**
 * Test script to validate the InfiniteScribe monorepo project structure
 * This script verifies that all required directories and files have been created correctly
 */

const fs = require('fs');
const path = require('path');

// ANSI color codes for terminal output
const colors = {
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  reset: '\x1b[0m'
};

// Helper functions
const exists = (filepath) => fs.existsSync(filepath);
const isDirectory = (filepath) => exists(filepath) && fs.statSync(filepath).isDirectory();
const isFile = (filepath) => exists(filepath) && fs.statSync(filepath).isFile();

// Project root
const projectRoot = path.resolve(__dirname, '../..');

// Test results
let totalTests = 0;
let passedTests = 0;
let failedTests = [];

// Test function
function test(description, condition, filepath) {
  totalTests++;
  if (condition) {
    passedTests++;
    console.log(`${colors.green}✓${colors.reset} ${description}`);
  } else {
    failedTests.push({ description, filepath });
    console.log(`${colors.red}✗${colors.reset} ${description}`);
    console.log(`  ${colors.yellow}Missing: ${filepath}${colors.reset}`);
  }
}

console.log(`${colors.blue}InfiniteScribe Project Structure Validation${colors.reset}\n`);

// Test root files
console.log('Checking root files...');
test('package.json exists', isFile(path.join(projectRoot, 'package.json')), 'package.json');
test('pnpm-workspace.yaml exists', isFile(path.join(projectRoot, 'pnpm-workspace.yaml')), 'pnpm-workspace.yaml');
test('tsconfig.json exists', isFile(path.join(projectRoot, 'tsconfig.json')), 'tsconfig.json');
test('.gitignore exists', isFile(path.join(projectRoot, '.gitignore')), '.gitignore');
test('.eslintrc.js exists', isFile(path.join(projectRoot, '.eslintrc.js')), '.eslintrc.js');
test('.eslintignore exists', isFile(path.join(projectRoot, '.eslintignore')), '.eslintignore');
test('.prettierrc.js exists', isFile(path.join(projectRoot, '.prettierrc.js')), '.prettierrc.js');
test('.prettierignore exists', isFile(path.join(projectRoot, '.prettierignore')), '.prettierignore');
test('.env.example exists', isFile(path.join(projectRoot, '.env.example')), '.env.example');
test('.dockerignore exists', isFile(path.join(projectRoot, '.dockerignore')), '.dockerignore');
test('docker-compose.yml exists', isFile(path.join(projectRoot, 'docker-compose.yml')), 'docker-compose.yml');
test('README.md exists', isFile(path.join(projectRoot, 'README.md')), 'README.md');

// Test directories
console.log('\nChecking directory structure...');
test('apps/ directory exists', isDirectory(path.join(projectRoot, 'apps')), 'apps/');
test('apps/frontend/ exists', isDirectory(path.join(projectRoot, 'apps/frontend')), 'apps/frontend/');
test('apps/api-gateway/ exists', isDirectory(path.join(projectRoot, 'apps/api-gateway')), 'apps/api-gateway/');


test('infrastructure/ directory exists', isDirectory(path.join(projectRoot, 'infrastructure')), 'infrastructure/');
test('docs/ directory exists', isDirectory(path.join(projectRoot, 'docs')), 'docs/');
test('scripts/ directory exists', isDirectory(path.join(projectRoot, 'scripts')), 'scripts/');


// Validate package.json content
console.log('\nValidating package.json configuration...');
try {
  const packageJson = JSON.parse(fs.readFileSync(path.join(projectRoot, 'package.json'), 'utf8'));
  
  test('package.json has correct name', packageJson.name === 'infinite-scribe', 'package.json name');
  test('package.json is private', packageJson.private === true, 'package.json private');
  test('package.json has engines.node', packageJson.engines && packageJson.engines.node, 'package.json engines.node');
  test('package.json has engines.pnpm', packageJson.engines && packageJson.engines.pnpm === '~8.15.0', 'package.json engines.pnpm');
  test('package.json has packageManager', packageJson.packageManager && packageJson.packageManager.startsWith('pnpm@8.15'), 'package.json packageManager');
  test('package.json has test:structure script', packageJson.scripts && packageJson.scripts['test:structure'], 'package.json scripts.test:structure');
} catch (error) {
  console.error(`${colors.red}Failed to parse package.json: ${error.message}${colors.reset}`);
}

// Validate pnpm-workspace.yaml content
console.log('\nValidating pnpm-workspace.yaml configuration...');
try {
  const workspaceContent = fs.readFileSync(path.join(projectRoot, 'pnpm-workspace.yaml'), 'utf8');
  test('pnpm-workspace.yaml includes apps/*', workspaceContent.includes("- 'apps/*'"), 'pnpm-workspace.yaml apps/*');
} catch (error) {
  console.error(`${colors.red}Failed to read pnpm-workspace.yaml: ${error.message}${colors.reset}`);
}

// Summary
console.log(`\n${colors.blue}Test Summary${colors.reset}`);
console.log(`Total tests: ${totalTests}`);
console.log(`Passed: ${colors.green}${passedTests}${colors.reset}`);
console.log(`Failed: ${colors.red}${failedTests.length}${colors.reset}`);

if (failedTests.length > 0) {
  console.log(`\n${colors.red}Failed tests:${colors.reset}`);
  failedTests.forEach(({ description, filepath }) => {
    console.log(`  - ${description} (${filepath})`);
  });
  process.exit(1);
} else {
  console.log(`\n${colors.green}✓ All tests passed! Project structure is valid.${colors.reset}`);
  process.exit(0);
}