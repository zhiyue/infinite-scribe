#!/bin/bash
# Backup development server data

set -e

# Configuration
DEV_SERVER="${DEV_SERVER:-192.168.2.201}"
DEV_USER="${DEV_USER:-zhiyue}"
PROJECT_DIR="~/workspace/mvp/infinite-scribe"
BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="infinitescribe_backup_${TIMESTAMP}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}InfiniteScribe Development Data Backup${NC}"
echo -e "${BLUE}======================================${NC}"
echo -e "Server: ${DEV_USER}@${DEV_SERVER}"
echo -e "Backup: ${BACKUP_NAME}"
echo ""

# Create local backup directory
mkdir -p "${BACKUP_DIR}"

# Check SSH connection
echo -e "${YELLOW}Checking SSH connection...${NC}"
if ! ssh -o ConnectTimeout=5 ${DEV_USER}@${DEV_SERVER} "echo 'SSH connection successful'" >/dev/null 2>&1; then
    echo -e "${RED}Failed to connect to ${DEV_USER}@${DEV_SERVER}${NC}"
    exit 1
fi
echo -e "${GREEN}✓ SSH connection verified${NC}"

# Create remote backup directory
echo -e "\n${YELLOW}Creating remote backup directory...${NC}"
ssh ${DEV_USER}@${DEV_SERVER} "mkdir -p ${PROJECT_DIR}/backups/${BACKUP_NAME}"

# Backup PostgreSQL
echo -e "\n${YELLOW}Backing up PostgreSQL databases...${NC}"
ssh ${DEV_USER}@${DEV_SERVER} "cd ${PROJECT_DIR} && \
    docker compose exec -T postgres pg_dumpall -U postgres > backups/${BACKUP_NAME}/postgres_all.sql"
echo -e "${GREEN}✓ PostgreSQL backup complete${NC}"

# Backup Redis
echo -e "\n${YELLOW}Backing up Redis data...${NC}"
ssh ${DEV_USER}@${DEV_SERVER} "cd ${PROJECT_DIR} && \
    docker compose exec -T redis redis-cli --rdb backups/${BACKUP_NAME}/redis.rdb BGSAVE && \
    sleep 2 && \
    docker compose cp redis:/data/dump.rdb backups/${BACKUP_NAME}/redis.rdb"
echo -e "${GREEN}✓ Redis backup complete${NC}"

# Backup Neo4j
echo -e "\n${YELLOW}Backing up Neo4j database...${NC}"
ssh ${DEV_USER}@${DEV_SERVER} "cd ${PROJECT_DIR} && \
    docker compose stop neo4j && \
    docker compose run --rm -v ${PROJECT_DIR}/backups/${BACKUP_NAME}:/backup neo4j \
        neo4j-admin database dump --to-path=/backup neo4j && \
    docker compose start neo4j"
echo -e "${GREEN}✓ Neo4j backup complete${NC}"

# Backup MinIO data
echo -e "\n${YELLOW}Backing up MinIO data...${NC}"
ssh ${DEV_USER}@${DEV_SERVER} "cd ${PROJECT_DIR} && \
    docker compose exec -T minio mc alias set myminio http://localhost:9000 minioadmin minioadmin && \
    docker compose exec -T minio mc mirror --overwrite myminio /backup/${BACKUP_NAME}/minio"
echo -e "${GREEN}✓ MinIO backup complete${NC}"

# Backup environment files
echo -e "\n${YELLOW}Backing up environment files...${NC}"
ssh ${DEV_USER}@${DEV_SERVER} "cd ${PROJECT_DIR} && \
    cp .env.* backups/${BACKUP_NAME}/ 2>/dev/null || true"
echo -e "${GREEN}✓ Environment files backup complete${NC}"

# Create tarball on remote
echo -e "\n${YELLOW}Creating backup archive...${NC}"
ssh ${DEV_USER}@${DEV_SERVER} "cd ${PROJECT_DIR}/backups && \
    tar -czf ${BACKUP_NAME}.tar.gz ${BACKUP_NAME}/"
echo -e "${GREEN}✓ Archive created${NC}"

# Download backup to local
echo -e "\n${YELLOW}Downloading backup to local machine...${NC}"
scp ${DEV_USER}@${DEV_SERVER}:${PROJECT_DIR}/backups/${BACKUP_NAME}.tar.gz ${BACKUP_DIR}/
echo -e "${GREEN}✓ Backup downloaded to ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz${NC}"

# Cleanup remote backup directory (keep tarball)
echo -e "\n${YELLOW}Cleaning up remote temporary files...${NC}"
ssh ${DEV_USER}@${DEV_SERVER} "cd ${PROJECT_DIR}/backups && rm -rf ${BACKUP_NAME}/"
echo -e "${GREEN}✓ Cleanup complete${NC}"

# Show backup info
BACKUP_SIZE=$(ls -lh ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz | awk '{print $5}')
echo -e "\n${BLUE}Backup Summary:${NC}"
echo -e "${BLUE}===============${NC}"
echo -e "File: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
echo -e "Size: ${BACKUP_SIZE}"
echo -e "Contents:"
echo -e "  - PostgreSQL databases (all)"
echo -e "  - Redis data snapshot"
echo -e "  - Neo4j database dump"
echo -e "  - MinIO object storage"
echo -e "  - Environment configuration files"

# Backup retention notice
echo -e "\n${YELLOW}Note: Consider implementing a backup retention policy${NC}"
echo -e "Current backups in ${BACKUP_DIR}:"
ls -lht ${BACKUP_DIR}/*.tar.gz 2>/dev/null | head -5 || echo "  No backups found"

echo -e "\n${GREEN}Backup completed successfully!${NC}"