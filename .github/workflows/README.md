# GitHub Actions Workflows

## Workflows Overview

### 1. Python CI (`python-ci.yml`)
- **Trigger**: Push/PR to main/develop branches
- **Jobs**: Linting, unit tests, integration tests
- **Purpose**: Ensure code quality and functionality

### 2. Security Scan (`security.yml`)
- **Trigger**: 
  - Push/PR to main/develop branches
  - Daily scheduled scan at 2 AM UTC
  - Manual trigger with options
- **Jobs**:
  - **Trivy**: Vulnerability scanning (CRITICAL only)
  - **Dependency Review**: PR dependency analysis
  - **Gitleaks**: Secret scanning
- **Purpose**: Identify security vulnerabilities and exposed secrets

## Security Scanning Strategy

### Blocking vs Non-blocking

The security workflow has flexible blocking behavior:

1. **PR and develop branch**: Blocks on CRITICAL vulnerabilities (default)
2. **Main branch pushes**: Reports but doesn't block (allows hotfixes)
3. **Scheduled scans**: Reports only (for monitoring)
4. **Manual runs**: Configurable via workflow dispatch

### Manual Trigger Options

When manually triggering the security workflow:
```yaml
fail-on-vulnerabilities: true/false  # Whether to fail on findings
```

### Vulnerability Severity Levels

Currently configured to scan for **CRITICAL** vulnerabilities only. To adjust:
- Edit `severity` in `security.yml`
- Options: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`

### Excluded Directories

The following are excluded from scanning:
- `node_modules`
- `dist`, `build`
- `.venv`, `__pycache__`
- `.git`

## Viewing Results

1. **GitHub Security Tab**: All findings are uploaded to the Security tab
2. **Workflow Summary**: Quick summary in the workflow run
3. **SARIF Reports**: Detailed results in `trivy-results.sarif`

## Local Testing

Run security scans locally:
```bash
# Install Trivy
brew install aquasecurity/trivy/trivy

# Run scan
trivy fs . --severity CRITICAL --skip-dirs node_modules,dist,build,.venv
```