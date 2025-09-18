/**
 * 创世设定详情模态窗口组件
 * 显示实际的阶段配置数据（只读查看）
 */

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Card, CardContent } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import {
  AlertCircle,
  Sparkles,
  Globe,
  Users,
  BookOpen,
  Copy,
  CheckCircle,
  Clock,
  Settings,
  FileText,
  Hash,
  List,
  Tag
} from 'lucide-react'
import { GenesisStage } from '@/types/enums'
import { useGenesisFlow } from '@/hooks/useGenesisFlow'
import { useStageConfig } from '@/hooks/useStageConfig'
import { useState } from 'react'


interface GenesisSettingsModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  stage: GenesisStage | null
  novelId: string
}


/**
 * 动态翻译英文术语到中文
 */
function translateToChineseTerm(englishTerm: string): string {
  const translations: Record<string, string> = {
    // 阶段相关
    'initial': '初始',
    'prompt': '提示',
    'world': '世界',
    'worldview': '世界观',
    'setting': '设定',
    'character': '角色',
    'characters': '角色',
    'people': '人物',
    'plot': '剧情',
    'story': '故事',
    'outline': '大纲',
    'finished': '完成',

    // 字段相关
    'count': '数量',
    'number': '数字',
    'amount': '数量',
    'level': '等级',
    'type': '类型',
    'style': '风格',
    'theme': '主题',
    'genre': '类型',
    'preference': '偏好',
    'preferences': '偏好',
    'requirement': '要求',
    'requirements': '要求',
    'element': '元素',
    'elements': '元素',
    'system': '系统',
    'structure': '结构',
    'complexity': '复杂度',
    'development': '发展',
    'focus': '重点',
    'relationship': '关系',
    'personality': '个性',
    'protagonist': '主角',
    'depth': '深度',
    'pacing': '节奏',
    'conflict': '冲突',
    'chapter': '章节',
    'subplot': '副线',
    'geography': '地理',
    'time': '时间',
    'period': '时期',
    'technology': '科技',
    'magic': '魔法',
    'cultural': '文化',
    'culture': '文化',
    'target': '目标',
    'word': '词',
    'special': '特殊',

    // 组合词处理
    'initial_prompt': '初始灵感',
    'world_view': '世界观',
    'plot_outline': '剧情大纲',
  }

  const term = englishTerm.toLowerCase()

  // 优先匹配完整词组
  if (translations[term]) {
    return translations[term]
  }

  // 分词翻译
  const words = term.split('_')
  const translatedWords = words.map(word => translations[word] || word)

  return translatedWords.join('')
}

/**
 * 动态获取阶段信息（基于阶段名称推断）
 */
function getStageInfo(stage: GenesisStage) {
  const stageStr = stage.toString().toLowerCase()

  // 动态推断图标
  let icon = FileText // 默认图标
  if (stageStr.includes('prompt') || stageStr.includes('initial')) icon = Sparkles
  else if (stageStr.includes('world') || stageStr.includes('setting')) icon = Globe
  else if (stageStr.includes('character') || stageStr.includes('people')) icon = Users
  else if (stageStr.includes('plot') || stageStr.includes('story') || stageStr.includes('outline')) icon = BookOpen

  // 智能翻译标题
  const title = translateToChineseTerm(stageStr)

  return {
    title,
    icon,
    description: `${title}配置详情`
  }
}




/**
 * 创世设定详情模态窗口主组件
 */
export function GenesisSettingsModal({
  open,
  onOpenChange,
  stage,
  novelId,
}: GenesisSettingsModalProps) {
  const { flow: _flow } = useGenesisFlow(novelId)

  if (!stage) return null

  const stageInfo = getStageInfo(stage)
  const { title, description } = stageInfo

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl max-h-[90vh] w-[95vw] p-0 gap-0">
        {/* 头部 */}
        <DialogHeader className="p-4 sm:p-6 pb-3 sm:pb-4 border-b bg-muted/20">
          <div className="flex items-center gap-3 sm:gap-4">
            <div className="p-2 sm:p-3 bg-primary/10 rounded-lg flex-shrink-0">
              <stageInfo.icon className="h-5 w-5 sm:h-6 sm:w-6 text-primary" />
            </div>
            <div className="min-w-0 flex-1">
              <DialogTitle className="text-lg sm:text-xl truncate">{title}</DialogTitle>
              <DialogDescription className="text-sm sm:text-base text-muted-foreground">
                {description}
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        {/* 内容区域 */}
        <div className="flex-1 overflow-hidden">
          <ScrollArea className="h-[70vh] sm:h-[75vh] px-4 sm:px-6 py-4 sm:py-6">
            <StageConfigDisplay stage={stage} novelId={novelId} />
          </ScrollArea>
        </div>
      </DialogContent>
    </Dialog>
  )
}

/**
 * 通用字段名格式化函数（中文显示）
 */
function formatFieldName(fieldName: string): string {
  // 优先使用翻译系统
  const translated = translateToChineseTerm(fieldName)

  // 如果翻译结果与原始字段名差异很大，说明翻译成功
  if (translated !== fieldName && translated.length > 0 && !translated.includes('_')) {
    return translated
  }

  // 否则使用标准格式化（首字母大写，去下划线）
  return fieldName
    .split('_')
    .map(word => translateToChineseTerm(word) || word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

/**
 * 数据字段渲染组件
 */
function DataFieldRenderer({
  label,
  value,
  type = 'text',
  icon: Icon,
  copyable = false
}: {
  label: string
  value: any
  type?: 'text' | 'number' | 'array' | 'object' | 'boolean'
  icon?: React.ElementType
  copyable?: boolean
}) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    if (typeof value === 'string') {
      await navigator.clipboard.writeText(value)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const renderValue = () => {
    if (value === null || value === undefined || value === '') {
      return <span className="text-muted-foreground italic">-</span>
    }

    switch (type) {
      case 'boolean':
        return (
          <Badge variant={value ? 'default' : 'secondary'}>
            {value ? '✓' : '✗'}
          </Badge>
        )
      case 'array':
        if (!Array.isArray(value) || value.length === 0) {
          return <span className="text-muted-foreground italic">-</span>
        }
        return (
          <div className="space-y-1">
            {value.map((item, index) => (
              <div key={index} className="flex items-center gap-2">
                <div className="w-1 h-1 bg-primary rounded-full flex-shrink-0" />
                <span className="text-sm">{String(item)}</span>
              </div>
            ))}
          </div>
        )
      case 'object':
        if (!value || typeof value !== 'object') {
          return <span className="text-muted-foreground italic">-</span>
        }
        return (
          <div className="space-y-2">
            {Object.entries(value).map(([key, val]) => (
              <div key={key} className="flex justify-between items-start gap-4">
                <span className="text-sm font-medium text-muted-foreground min-w-0">
                  {formatFieldName(key)}:
                </span>
                <span className="text-sm text-right flex-1">{String(val)}</span>
              </div>
            ))}
          </div>
        )
      case 'number':
        return <span className="font-mono">{value}</span>
      default:
        return <span className="break-words">{String(value)}</span>
    }
  }

  return (
    <div className="group flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 p-3 sm:p-4 rounded-lg border border-border/50 bg-card/50 hover:bg-card/80 hover:border-border/80 transition-all duration-200">
      <div className="flex items-start gap-3 min-w-0 flex-1">
        {Icon && <Icon className="h-4 w-4 text-muted-foreground mt-0.5 flex-shrink-0" />}
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-foreground mb-1 sm:mb-2">{label}</p>
          <div className="text-sm text-muted-foreground">
            {renderValue()}
          </div>
        </div>
      </div>
      {copyable && typeof value === 'string' && value && (
        <Button
          variant="ghost"
          size="sm"
          className="h-7 w-7 p-0 opacity-0 group-hover:opacity-60 hover:!opacity-100 transition-opacity duration-200 flex-shrink-0 self-start sm:self-center"
          onClick={handleCopy}
          title="复制到剪贴板"
        >
          {copied ? (
            <CheckCircle className="h-3 w-3 text-green-600" />
          ) : (
            <Copy className="h-3 w-3" />
          )}
        </Button>
      )}
    </div>
  )
}

/**
 * 阶段配置显示组件
 */
function StageConfigDisplay({ stage, novelId }: { stage: GenesisStage; novelId: string }) {
  const { flow } = useGenesisFlow(novelId)

  // 获取当前阶段ID
  const currentStageId = flow?.current_stage_id || ''

  // 获取阶段配置数据
  const {
    schema,
    currentConfig,
    session,
    isLoading,
    loadError,
    isReady
  } = useStageConfig(stage, currentStageId)

  // 从schema中获取字段信息
  const getFieldInfo = (fieldName: string) => {
    if (!schema?.properties) return { title: fieldName, description: '' }
    const field = schema.properties[fieldName]
    return {
      title: field?.title || fieldName,
      description: field?.description || '',
      type: field?.type || 'string'
    }
  }

  // 完全动态的字段图标推断（基于语义分析）
  const getFieldIcon = (fieldName: string, fieldType: string, fieldValue?: any) => {
    const name = fieldName.toLowerCase()

    // 基于语义关键词动态推断
    if (name.includes('count') || name.includes('number') || name.includes('amount') ||
        name.includes('quantity') || name.includes('size') || name.includes('length')) {
      return Hash
    }

    if (name.includes('time') || name.includes('date') || name.includes('created') ||
        name.includes('updated') || name.includes('period') || name.includes('duration')) {
      return Clock
    }

    if (name.includes('setting') || name.includes('world') || name.includes('geography') ||
        name.includes('location') || name.includes('place') || name.includes('environment')) {
      return Globe
    }

    if (name.includes('character') || name.includes('people') || name.includes('person') ||
        name.includes('protagonist') || name.includes('relationship') || name.includes('personality')) {
      return Users
    }

    if (name.includes('magic') || name.includes('spell') || name.includes('power') ||
        name.includes('ability') || name.includes('supernatural') || name.includes('fantasy')) {
      return Sparkles
    }

    if (name.includes('story') || name.includes('plot') || name.includes('narrative') ||
        name.includes('structure') || name.includes('outline') || name.includes('chapter')) {
      return BookOpen
    }

    if (name.includes('list') || name.includes('items') || name.includes('elements') ||
        name.includes('preferences') || name.includes('requirements') || name.includes('types')) {
      return List
    }

    if (name.includes('style') || name.includes('config') || name.includes('setting') ||
        name.includes('option') || name.includes('preference') || name.includes('level')) {
      return Settings
    }

    if (name.includes('genre') || name.includes('category') || name.includes('type') ||
        name.includes('kind') || name.includes('class') || name.includes('tag')) {
      return Tag
    }

    // 基于数据类型推断
    if (fieldType === 'array' || Array.isArray(fieldValue)) return List
    if (fieldType === 'number' || fieldType === 'integer') return Hash
    if (fieldType === 'boolean') return Settings
    if (fieldType === 'object' && fieldValue && typeof fieldValue === 'object') return FileText

    // 默认图标
    return FileText
  }

  // 从 schema 动态生成字段配置
  const generateFieldConfigs = () => {
    if (!schema?.properties || !currentConfig) return []

    const configs = Object.keys(currentConfig)
      .filter(key => currentConfig[key] !== undefined)
      .map(key => {
        const fieldInfo = getFieldInfo(key)
        const value = currentConfig[key]
        const fieldType = Array.isArray(value) ? 'array'
          : typeof value === 'object' && value !== null ? 'object'
          : typeof value === 'boolean' ? 'boolean'
          : typeof value === 'number' ? 'number'
          : 'string'

        return {
          key,
          icon: getFieldIcon(key, fieldType, value),
          label: fieldInfo.title || formatFieldName(key),
          priority: calculateFieldPriority(key, fieldInfo, value)
        }
      })
      .sort((a, b) => a.priority - b.priority)

    return configs
  }


  // 动态计算字段优先级（基于语义和 schema 信息）
  const calculateFieldPriority = (fieldName: string, fieldInfo: any, value: any): number => {
    const name = fieldName.toLowerCase()

    // 基于 schema 的优先级信息
    if (fieldInfo.priority !== undefined) return fieldInfo.priority

    // 核心业务字段 - 最高优先级
    if (name.includes('genre') || name.includes('theme') || name.includes('style')) return 10
    if (name.includes('title') || name.includes('name') || name.includes('type')) return 20

    // 重要配置字段
    if (name.includes('count') || name.includes('level') || name.includes('preference')) return 30
    if (name.includes('structure') || name.includes('system') || name.includes('complexity')) return 40

    // 一般配置字段
    if (name.includes('setting') || name.includes('geography') || name.includes('culture')) return 50
    if (name.includes('character') || name.includes('relationship') || name.includes('personality')) return 60
    if (name.includes('story') || name.includes('plot') || name.includes('narrative')) return 70

    // 详细配置字段
    if (name.includes('requirements') || name.includes('elements') || name.includes('preferences')) return 80

    // 系统字段 - 最低优先级
    if (name.includes('id') || name.includes('uuid')) return 900
    if (name.includes('created') || name.includes('updated') || name.includes('time') || name.includes('date')) return 950

    // 基于数据类型推断优先级
    if (typeof value === 'string' && value.length > 0) return 100
    if (typeof value === 'number') return 110
    if (typeof value === 'boolean') return 120
    if (Array.isArray(value) && value.length > 0) return 130
    if (typeof value === 'object' && value !== null) return 140

    // 默认优先级
    return 500
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="flex items-center gap-3 text-muted-foreground">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
          <span>正在加载配置数据...</span>
        </div>
      </div>
    )
  }

  if (loadError) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          加载配置数据失败：{loadError instanceof Error ? loadError.message : '未知错误'}
        </AlertDescription>
      </Alert>
    )
  }

  if (!isReady || !currentConfig) {
    return (
      <Alert>
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          当前阶段暂无配置数据，请先进行阶段配置设置。
        </AlertDescription>
      </Alert>
    )
  }

  const fieldConfigs = generateFieldConfigs()
  const hasData = fieldConfigs.length > 0

  return (
    <div className="space-y-6">

      <Card>
        <CardContent className="space-y-4 pt-6">
          {!hasData ? (
            <div className="text-center py-8 text-muted-foreground">
              <Settings className="h-12 w-12 mx-auto mb-3 opacity-50" />
              <p>暂无配置数据</p>
            </div>
          ) : (
            <div className="space-y-3">
              {fieldConfigs.map(({ key, icon, label }) => {
                const value = currentConfig[key]
                if (value === undefined) return null

                const type = Array.isArray(value) ? 'array'
                  : typeof value === 'object' && value !== null ? 'object'
                  : typeof value === 'boolean' ? 'boolean'
                  : typeof value === 'number' ? 'number'
                  : 'text'

                return (
                  <DataFieldRenderer
                    key={key}
                    label={label}
                    value={value}
                    type={type}
                    icon={icon}
                    copyable={type === 'text' && typeof value === 'string'}
                  />
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* 动态会话信息显示 */}
      {session && Object.keys(session).length > 0 && (
        <Card>
          <CardContent className="pt-6">
            <div className="space-y-3">
              {Object.entries(session)
                .filter(([, value]) => value !== undefined && value !== null && value !== '')
                .map(([fieldKey, value]) => (
                  <DataFieldRenderer
                    key={fieldKey}
                    label={formatFieldName(fieldKey)}
                    value={value}
                    type={typeof value === 'object' ? 'object' : 'text'}
                    icon={getFieldIcon(fieldKey, typeof value, value)}
                    copyable={typeof value === 'string'}
                  />
                ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
