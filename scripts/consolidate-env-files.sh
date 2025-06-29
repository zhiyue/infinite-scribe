#!/bin/bash
# Consolidate multiple .env files into a cleaner structure
# New structure: .env.local, .env.dev, .env.test, .env.example

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "🔄 Consolidating .env files..."

# Create backup directory
BACKUP_DIR=".env-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup all existing .env files
echo "📦 Backing up existing .env files to $BACKUP_DIR/"
find . -maxdepth 3 -name ".env*" -type f -exec cp {} "$BACKUP_DIR/" \; 2>/dev/null || true

# Step 1: Create .env.dev from current infrastructure setup
echo "🏗️  Creating .env.dev (Development Server)"
cat > .env.dev << 'EOF'
# Development Server Configuration (192.168.2.201)
# This file is for the development infrastructure server

# PostgreSQL Database
POSTGRES_HOST=192.168.2.201
POSTGRES_PORT=5432
POSTGRES_DB=infinite_scribe
POSTGRES_USER=postgres
POSTGRES_PASSWORD=devPostgres123!

# Redis Cache
REDIS_HOST=192.168.2.201
REDIS_PORT=6379
REDIS_PASSWORD=devRedis123!

# Neo4j Graph Database
NEO4J_HOST=192.168.2.201
NEO4J_PORT=7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=devNeo4j123!
NEO4J_URI=bolt://192.168.2.201:7687

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Frontend Configuration
NEXT_PUBLIC_API_URL=http://192.168.2.201:8000
PORT=3000

# Service Configuration
NODE_ENV=development
EOF

# Step 2: Create .env.local from backend.local
echo "💻 Creating .env.local (Local Development)"
cat > .env.local << 'EOF'
# Local Development Configuration
# This file is for local development with Docker Compose

# PostgreSQL Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=infinite_scribe
POSTGRES_USER=postgres
POSTGRES_PASSWORD=devPostgres123!

# Redis Cache
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=devRedis123!

# Neo4j Graph Database
NEO4J_HOST=localhost
NEO4J_PORT=7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=devNeo4j123!
NEO4J_URI=bolt://localhost:7687

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Frontend Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
PORT=3000

# Service Configuration
NODE_ENV=development
EOF

# Step 3: Update .env.test with proper test configuration
echo "🧪 Updating .env.test (Test Environment)"
cat > .env.test << 'EOF'
# Test Environment Configuration
# This file is for test runs on the test machine

# Test Machine Configuration
TEST_MACHINE_IP=${TEST_MACHINE_IP:-192.168.2.202}

# PostgreSQL Database
POSTGRES_HOST=${TEST_MACHINE_IP}
POSTGRES_PORT=5432
POSTGRES_DB=infinite_scribe_test
POSTGRES_USER=postgres
POSTGRES_PASSWORD=testPostgres123!

# Redis Cache
REDIS_HOST=${TEST_MACHINE_IP}
REDIS_PORT=6379
REDIS_PASSWORD=testRedis123!

# Neo4j Graph Database
NEO4J_HOST=${TEST_MACHINE_IP}
NEO4J_PORT=7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=testNeo4j123!
NEO4J_URI=bolt://${TEST_MACHINE_IP}:7687

# Docker Configuration for Testcontainers
USE_REMOTE_DOCKER=true
REMOTE_DOCKER_HOST=tcp://${TEST_MACHINE_IP}:2375
DISABLE_RYUK=false

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Service Configuration
NODE_ENV=test
EOF

# Step 4: Create comprehensive .env.example
echo "📋 Creating .env.example (Template)"
cat > .env.example << 'EOF'
# InfiniteScribe Environment Configuration Template
# Copy this file to .env.local, .env.dev, or .env.test and update values

# PostgreSQL Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=infinite_scribe
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_postgres_password

# Redis Cache
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password

# Neo4j Graph Database
NEO4J_HOST=localhost
NEO4J_PORT=7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password
NEO4J_URI=bolt://localhost:7687

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Frontend Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
PORT=3000

# Service Configuration
NODE_ENV=development

# Optional Services (uncomment as needed)
# MILVUS_HOST=localhost
# MILVUS_PORT=19530
# MINIO_HOST=localhost
# MINIO_PORT=9000
# MINIO_ACCESS_KEY=minioadmin
# MINIO_SECRET_KEY=minioadmin
# KAFKA_HOST=localhost
# KAFKA_PORT=9092
EOF

# Step 5: Update .gitignore
echo "📝 Updating .gitignore"
if ! grep -q "^\.env\.local$" .gitignore; then
    echo -e "\n# Environment files\n.env\n.env.local\n.env.dev\n.env.test\n!.env.example" >> .gitignore
fi

# Step 6: Remove old symlink if exists
if [ -L .env ]; then
    rm .env
fi

# Step 7: Create symlink to .env.local by default
echo "🔗 Creating symlink: .env -> .env.local"
ln -s .env.local .env

# Step 8: Update test script to use .env.test
echo "🔧 Updating test script"
sed -i 's/\.env\.remote-docker/.env.test/g' scripts/testing/run-tests.sh 2>/dev/null || true

# Step 9: Clean up old files (commented out for safety)
echo "🧹 Old files to remove (manual action required):"
echo "   rm .env.infrastructure"
echo "   rm .env.backend.local"
echo "   rm .env.backend.example"
echo "   rm .env.frontend.example"
echo "   rm .env.agents.example"
echo "   rm .env.remote-docker"
echo "   rm .env.all-in-one.backup"
echo "   rm apps/backend/.env.test"
echo "   rm apps/backend/.env.ci"

echo ""
echo "✅ Consolidation complete!"
echo ""
echo "📋 New structure:"
echo "   .env         -> Symlink to active environment"
echo "   .env.local   -> Local development with Docker"
echo "   .env.dev     -> Development server (192.168.2.201)"
echo "   .env.test    -> Test environment"
echo "   .env.example -> Template for new environments"
echo ""
echo "🔄 To switch environments:"
echo "   ln -sf .env.local .env    # For local development"
echo "   ln -sf .env.dev .env      # For dev server"
echo "   ln -sf .env.test .env     # For testing"
echo ""
echo "⚠️  Please review the backup in $BACKUP_DIR/ and manually remove old files"
