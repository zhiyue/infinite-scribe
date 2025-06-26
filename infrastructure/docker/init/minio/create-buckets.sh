#!/bin/bash

# Wait for MinIO to be ready
echo "Waiting for MinIO to be ready..."
sleep 10

# Configure mc (MinIO Client) with the MinIO service
mc alias set myminio http://minio:9000 ${MINIO_ROOT_USER} ${MINIO_ROOT_PASSWORD}

# Create the novels bucket
echo "Creating novels bucket..."
mc mb myminio/novels

# Set bucket policy to allow read/write access
echo "Setting bucket policy..."
mc policy set download myminio/novels

echo "MinIO initialization complete!"