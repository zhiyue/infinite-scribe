# GitHub Security Setup

## Enabling Security Features

If you encounter "Resource not accessible by integration" errors in GitHub Actions, follow these steps:

### 1. Enable GitHub Advanced Security (for private repositories)

1. Go to Settings → Security & analysis
2. Enable:
   - Dependency graph
   - Dependabot alerts
   - Dependabot security updates
   - GitHub Advanced Security (if available)
   - Code scanning

### 2. Verify Workflow Permissions

The workflow already includes the necessary permissions:
```yaml
permissions:
  contents: read
  security-events: write
  actions: read
```

### 3. For Forks and Pull Requests

The workflow is configured to skip SARIF uploads for pull requests from forks:
```yaml
if: always() && (github.event_name != 'pull_request' || github.event.pull_request.head.repo.full_name == github.repository)
```

### 4. Alternative: Disable SARIF Upload

If you don't need security scanning results in GitHub's Security tab, you can comment out or remove the upload step:
```yaml
# - name: Upload Trivy scan results
#   uses: github/codeql-action/upload-sarif@v3
#   ...
```

The Trivy scan will still run and fail the workflow if vulnerabilities are found, but results won't be uploaded to GitHub's security dashboard.