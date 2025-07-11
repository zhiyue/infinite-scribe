import { Activity, Server, Database, Clock, AlertCircle, CheckCircle } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useHealthCheck } from '@/hooks/useHealthCheck'

export default function GlobalMonitoring() {
  const { data: health, isLoading, error } = useHealthCheck()

  const services = [
    {
      name: 'API 网关',
      status: health?.status === 'healthy' ? 'healthy' : 'unhealthy',
      icon: Server,
      description: '处理所有客户端请求',
      metrics: {
        uptime: '99.9%',
        requests: '1.2M/天',
        latency: '45ms',
      },
    },
    {
      name: '数据库',
      status: health?.services?.database || 'unknown',
      icon: Database,
      description: 'PostgreSQL 主数据库',
      metrics: {
        connections: '120/500',
        storage: '45GB/100GB',
        queries: '850K/天',
      },
    },
    {
      name: '缓存服务',
      status: health?.services?.redis || 'unknown',
      icon: Server,
      description: 'Redis 缓存层',
      metrics: {
        memory: '2.1GB/8GB',
        hitRate: '94%',
        operations: '5M/天',
      },
    },
    {
      name: '消息队列',
      status: health?.services?.kafka || 'unknown',
      icon: Activity,
      description: 'Kafka 消息服务',
      metrics: {
        topics: '12',
        messages: '500K/天',
        lag: '< 100ms',
      },
    },
  ]

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'text-green-600'
      case 'unhealthy':
        return 'text-red-600'
      default:
        return 'text-yellow-600'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="h-5 w-5 text-green-600" />
      case 'unhealthy':
        return <AlertCircle className="h-5 w-5 text-red-600" />
      default:
        return <Clock className="h-5 w-5 text-yellow-600" />
    }
  }

  return (
    <div className="container mx-auto py-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold">全局监控</h1>
        <p className="mt-2 text-muted-foreground">实时监控系统各项服务的运行状态</p>
      </div>

      {/* 整体状态 */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>系统整体状态</CardTitle>
          <CardDescription>
            最后更新: {health?.timestamp ? new Date(health.timestamp).toLocaleString() : '未知'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2">
            {isLoading && <Clock className="h-5 w-5 animate-spin" />}
            {error && <AlertCircle className="h-5 w-5 text-red-600" />}
            {health && getStatusIcon(health.status)}
            <span
              className={cn('text-lg font-medium', getStatusColor(health?.status || 'unknown'))}
            >
              {isLoading
                ? '检查中...'
                : error
                  ? '检查失败'
                  : health?.status === 'healthy'
                    ? '运行正常'
                    : '存在问题'}
            </span>
          </div>
        </CardContent>
      </Card>

      {/* 服务状态网格 */}
      <div className="grid gap-4 md:grid-cols-2">
        {services.map((service) => {
          const Icon = service.icon
          return (
            <Card key={service.name}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Icon className="h-6 w-6 text-muted-foreground" />
                    <div>
                      <CardTitle className="text-lg">{service.name}</CardTitle>
                      <CardDescription>{service.description}</CardDescription>
                    </div>
                  </div>
                  {getStatusIcon(service.status)}
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {Object.entries(service.metrics).map(([key, value]) => (
                    <div key={key} className="flex justify-between text-sm">
                      <span className="text-muted-foreground">
                        {key === 'uptime' && '运行时间'}
                        {key === 'requests' && '请求量'}
                        {key === 'latency' && '延迟'}
                        {key === 'connections' && '连接数'}
                        {key === 'storage' && '存储使用'}
                        {key === 'queries' && '查询量'}
                        {key === 'memory' && '内存使用'}
                        {key === 'hitRate' && '命中率'}
                        {key === 'operations' && '操作数'}
                        {key === 'topics' && '主题数'}
                        {key === 'messages' && '消息量'}
                        {key === 'lag' && '延迟'}
                      </span>
                      <span className="font-medium">{value}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* 系统指标 */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle>系统性能指标</CardTitle>
          <CardDescription>过去 24 小时的平均值</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-4">
            <div>
              <p className="text-sm text-muted-foreground">CPU 使用率</p>
              <p className="text-2xl font-bold">42%</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">内存使用率</p>
              <p className="text-2xl font-bold">68%</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">磁盘 I/O</p>
              <p className="text-2xl font-bold">125 MB/s</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">网络流量</p>
              <p className="text-2xl font-bold">850 MB/s</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

// 工具函数
function cn(...classes: string[]) {
  return classes.filter(Boolean).join(' ')
}
