# SSE Implementation Fix Plan

## Stage 1: Fix Critical Authentication Issue

**Goal**: Make SSE connection work by fixing token mismatch
**Success Criteria**: SSE connections establish successfully
**Tests**: Connection test with proper SSE token
**Status**: Not Started

### Implementation:

#### 1.1 Add SSE Token Service Method
```typescript
// apps/frontend/src/services/auth/auth-service.ts
async createSSEToken(): Promise<{ sse_token: string; expires_at: string }> {
  const response = await this.apiClient.post('/api/v1/auth/sse-token')
  return response.data
}
```

#### 1.2 Update SSE Service
```typescript
// apps/frontend/src/services/sseService.ts
class SSEService {
  private sseToken: string | null = null
  private sseTokenExpiry: number | null = null

  private async refreshSSEToken(): Promise<string | null> {
    try {
      const tokenData = await authService.createSSEToken()
      this.sseToken = tokenData.sse_token
      this.sseTokenExpiry = new Date(tokenData.expires_at).getTime()
      return this.sseToken
    } catch (error) {
      console.error('[SSE] Failed to create SSE token:', error)
      return null
    }
  }

  async connect(endpoint = '/api/v1/events/stream'): Promise<void> {
    // ... existing validation ...

    const url = new URL(endpoint, this.baseURL)
    
    // Get SSE token
    const sseToken = await this.refreshSSEToken()
    if (!sseToken) {
      this.setState(SSEConnectionState.ERROR)
      this.notifyErrorListeners(new Error('Failed to obtain SSE token'))
      return
    }
    
    // Use correct parameter name
    url.searchParams.set('sse_token', sseToken)
    
    // ... rest of connection logic ...
  }
}
```

## Stage 2: Improve Security

**Goal**: Remove tokens from URL, implement secure token passing
**Success Criteria**: No tokens visible in URLs or logs
**Tests**: Security audit passes
**Status**: Not Started

### Implementation:

#### 2.1 Backend: Session-Based Token Exchange
```python
# apps/backend/src/routers/events.py
@router.post("/api/v1/events/session")
async def create_sse_session(
    current_user: User = Depends(get_current_user),
    redis: Redis = Depends(get_redis)
):
    """Create a temporary session for SSE connection"""
    session_id = secrets.token_urlsafe(32)
    sse_token = create_sse_token_for_user(current_user.id)
    
    # Store in Redis with 30-second TTL
    await redis.setex(
        f"sse:session:{session_id}",
        30,
        json.dumps({
            "user_id": current_user.id,
            "token": sse_token,
            "created_at": datetime.utcnow().isoformat()
        })
    )
    
    return {"session_id": session_id}

@router.get("/api/v1/events/stream")
async def sse_stream(
    request: Request,
    session_id: str = Query(...),
    redis: Redis = Depends(get_redis)
):
    """Establish SSE connection using session ID"""
    # Retrieve and validate session
    session_data = await redis.get(f"sse:session:{session_id}")
    if not session_data:
        raise HTTPException(401, "Invalid or expired session")
    
    # Delete session (one-time use)
    await redis.delete(f"sse:session:{session_id}")
    
    session = json.loads(session_data)
    user_id = session["user_id"]
    
    # Continue with existing SSE logic
    return await create_sse_response(request, user_id)
```

#### 2.2 Frontend: Use Session ID
```typescript
// apps/frontend/src/services/sseService.ts
private async createSSESession(): Promise<string | null> {
  try {
    const response = await fetch(`${this.baseURL}/api/v1/events/session`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authService.getAccessToken()}`,
        'Content-Type': 'application/json',
      },
    })
    
    if (response.ok) {
      const data = await response.json()
      return data.session_id
    }
  } catch (error) {
    console.error('[SSE] Failed to create session:', error)
  }
  return null
}

async connect(endpoint = '/api/v1/events/stream'): Promise<void> {
  const sessionId = await this.createSSESession()
  if (!sessionId) {
    throw new Error('Failed to create SSE session')
  }
  
  const url = new URL(endpoint, this.baseURL)
  url.searchParams.set('session_id', sessionId)
  
  this.eventSource = new EventSource(url.toString())
  // ... rest of logic ...
}
```

## Stage 3: Add Connection Health Monitoring

**Goal**: Detect and recover from stale connections
**Success Criteria**: Auto-reconnect within 30 seconds of connection loss
**Tests**: Simulate network interruptions
**Status**: Not Started

### Implementation:

```typescript
// apps/frontend/src/services/sseService.ts
class SSEService {
  private heartbeatMonitor: HeartbeatMonitor | null = null

  private setupHeartbeatMonitor(): void {
    this.heartbeatMonitor = new HeartbeatMonitor({
      expectedInterval: 15000, // Backend sends ping every 15s
      timeout: 30000, // Consider dead after 30s
      onTimeout: () => {
        console.warn('[SSE] Heartbeat timeout, reconnecting...')
        this.reconnect()
      },
    })

    // Listen for ping events
    this.eventSource?.addEventListener('ping', () => {
      this.heartbeatMonitor?.recordHeartbeat()
    })
  }
}

class HeartbeatMonitor {
  private lastHeartbeat: number = Date.now()
  private checkInterval: NodeJS.Timeout | null = null

  constructor(private config: HeartbeatConfig) {
    this.startMonitoring()
  }

  recordHeartbeat(): void {
    this.lastHeartbeat = Date.now()
  }

  private startMonitoring(): void {
    this.checkInterval = setInterval(() => {
      const elapsed = Date.now() - this.lastHeartbeat
      if (elapsed > this.config.timeout) {
        this.config.onTimeout()
      }
    }, 5000)
  }

  destroy(): void {
    if (this.checkInterval) {
      clearInterval(this.checkInterval)
    }
  }
}
```

## Stage 4: Implement Event Filtering

**Goal**: Allow clients to subscribe to specific event types
**Success Criteria**: Reduced bandwidth and processing overhead
**Tests**: Verify filtered events delivery
**Status**: Not Started

### Implementation:

```typescript
// apps/frontend/src/services/sseService.ts
interface SSEConnectOptions {
  endpoint?: string
  eventTypes?: string[]
  metadata?: Record<string, string>
}

async connect(options: SSEConnectOptions = {}): Promise<void> {
  const {
    endpoint = '/api/v1/events/stream',
    eventTypes = [],
    metadata = {},
  } = options

  const sessionId = await this.createSSESession()
  if (!sessionId) {
    throw new Error('Failed to create SSE session')
  }

  const url = new URL(endpoint, this.baseURL)
  url.searchParams.set('session_id', sessionId)
  
  // Add event type filters
  if (eventTypes.length > 0) {
    url.searchParams.set('events', eventTypes.join(','))
  }
  
  // Add metadata
  Object.entries(metadata).forEach(([key, value]) => {
    url.searchParams.set(`meta_${key}`, value)
  })

  this.eventSource = new EventSource(url.toString())
  // ... rest of logic ...
}

// Usage
sseService.connect({
  eventTypes: ['novel.created', 'chapter.updated'],
  metadata: { client_version: '1.0.0' }
})
```

## Stage 5: Add Comprehensive Testing

**Goal**: Ensure reliability and catch regressions
**Success Criteria**: 90% test coverage for SSE code
**Tests**: Unit, integration, and E2E tests
**Status**: Not Started

### Test Files to Create:

1. `apps/frontend/src/services/__tests__/sseService.test.ts`
2. `apps/frontend/src/hooks/__tests__/useSSE.test.ts`
3. `apps/frontend/e2e/sse-connection.spec.ts`
4. `apps/backend/tests/test_sse_endpoints.py`

## Timeline

- **Week 1**: Complete Stages 1-2 (Critical fixes)
- **Week 2**: Complete Stages 3-4 (Enhancements)
- **Week 3**: Complete Stage 5 (Testing)

## Success Metrics

- Zero authentication errors in production
- < 1% connection failure rate
- < 5 seconds average reconnection time
- 100% event delivery for connected clients