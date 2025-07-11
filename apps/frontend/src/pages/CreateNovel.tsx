import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChevronRight, ChevronLeft, Sparkles, BookOpen, Users, Globe } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'

// 步骤配置
const steps = [
  { id: 1, title: '基本信息', icon: BookOpen },
  { id: 2, title: '世界观设定', icon: Globe },
  { id: 3, title: '角色设定', icon: Users },
  { id: 4, title: 'AI 配置', icon: Sparkles },
]

export default function CreateNovel() {
  const navigate = useNavigate()
  const [currentStep, setCurrentStep] = useState(1)
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    genre: '',
    worldSetting: '',
    mainCharacters: '',
    aiAssistLevel: 'medium',
  })

  const handleNext = () => {
    if (currentStep < steps.length) {
      setCurrentStep(currentStep + 1)
    }
  }

  const handlePrev = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1)
    }
  }

  const handleSubmit = () => {
    // TODO: 提交创建项目的逻辑
    console.log('创建项目:', formData)
    navigate('/dashboard')
  }

  const renderStepContent = () => {
    switch (currentStep) {
      case 1:
        return <BasicInfoStep formData={formData} setFormData={setFormData} />
      case 2:
        return <WorldSettingStep formData={formData} setFormData={setFormData} />
      case 3:
        return <CharacterStep formData={formData} setFormData={setFormData} />
      case 4:
        return <AIConfigStep formData={formData} setFormData={setFormData} />
      default:
        return null
    }
  }

  return (
    <div className="container mx-auto max-w-4xl py-8">
      {/* 步骤指示器 */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          {steps.map((step, index) => {
            const Icon = step.icon
            return (
              <div key={step.id} className="flex items-center">
                <div
                  className={cn(
                    'flex h-10 w-10 items-center justify-center rounded-full border-2',
                    currentStep >= step.id
                      ? 'border-primary bg-primary text-primary-foreground'
                      : 'border-muted-foreground text-muted-foreground',
                  )}
                >
                  <Icon className="h-5 w-5" />
                </div>
                <span
                  className={cn(
                    'ml-2 text-sm font-medium',
                    currentStep >= step.id ? 'text-foreground' : 'text-muted-foreground',
                  )}
                >
                  {step.title}
                </span>
                {index < steps.length - 1 && (
                  <div
                    className={cn(
                      'mx-4 h-0.5 w-full',
                      currentStep > step.id ? 'bg-primary' : 'bg-muted',
                    )}
                  />
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* 步骤内容 */}
      <Card>
        <CardHeader>
          <CardTitle>{steps[currentStep - 1].title}</CardTitle>
          <CardDescription>请填写以下信息，AI 将根据您的设定协助创作</CardDescription>
        </CardHeader>
        <CardContent>{renderStepContent()}</CardContent>
      </Card>

      {/* 导航按钮 */}
      <div className="mt-6 flex justify-between">
        <Button variant="outline" onClick={handlePrev} disabled={currentStep === 1}>
          <ChevronLeft className="mr-2 h-4 w-4" />
          上一步
        </Button>

        {currentStep < steps.length ? (
          <Button onClick={handleNext}>
            下一步
            <ChevronRight className="ml-2 h-4 w-4" />
          </Button>
        ) : (
          <Button onClick={handleSubmit}>
            <Sparkles className="mr-2 h-4 w-4" />
            开始创作
          </Button>
        )}
      </div>
    </div>
  )
}

// 表单数据类型
interface FormData {
  title: string
  description: string
  genre: string
  worldSetting: string
  mainCharacters: string
  aiAssistLevel: string
}

// 步骤组件的 Props 类型
interface StepProps {
  formData: FormData
  setFormData: (data: FormData) => void
}

// 基本信息步骤
function BasicInfoStep({ formData, setFormData }: StepProps) {
  return (
    <div className="space-y-4">
      <div>
        <Label htmlFor="title">作品标题</Label>
        <Input
          id="title"
          placeholder="输入您的作品标题"
          value={formData.title}
          onChange={(e) => setFormData({ ...formData, title: e.target.value })}
        />
      </div>
      <div>
        <Label htmlFor="description">作品简介</Label>
        <Textarea
          id="description"
          placeholder="简要描述您的作品内容"
          rows={4}
          value={formData.description}
          onChange={(e) => setFormData({ ...formData, description: e.target.value })}
        />
      </div>
      <div>
        <Label htmlFor="genre">作品类型</Label>
        <Input
          id="genre"
          placeholder="如：玄幻、都市、科幻等"
          value={formData.genre}
          onChange={(e) => setFormData({ ...formData, genre: e.target.value })}
        />
      </div>
    </div>
  )
}

// 世界观设定步骤
function WorldSettingStep({ formData, setFormData }: StepProps) {
  return (
    <div className="space-y-4">
      <div>
        <Label htmlFor="worldSetting">世界观设定</Label>
        <Textarea
          id="worldSetting"
          placeholder="描述您作品的世界观，包括时代背景、地理环境、社会体系等"
          rows={8}
          value={formData.worldSetting}
          onChange={(e) => setFormData({ ...formData, worldSetting: e.target.value })}
        />
      </div>
    </div>
  )
}

// 角色设定步骤
function CharacterStep({ formData, setFormData }: StepProps) {
  return (
    <div className="space-y-4">
      <div>
        <Label htmlFor="mainCharacters">主要角色设定</Label>
        <Textarea
          id="mainCharacters"
          placeholder="描述主要角色的姓名、性格、背景等信息"
          rows={8}
          value={formData.mainCharacters}
          onChange={(e) => setFormData({ ...formData, mainCharacters: e.target.value })}
        />
      </div>
    </div>
  )
}

// AI 配置步骤
function AIConfigStep({ formData, setFormData }: StepProps) {
  return (
    <div className="space-y-4">
      <div>
        <Label>AI 辅助程度</Label>
        <div className="mt-2 space-y-2">
          {[
            { value: 'low', label: '低 - 仅提供基础建议' },
            { value: 'medium', label: '中 - 提供详细建议和优化' },
            { value: 'high', label: '高 - 深度参与创作过程' },
          ].map((option) => (
            <label key={option.value} className="flex items-center space-x-2">
              <input
                type="radio"
                name="aiAssistLevel"
                value={option.value}
                checked={formData.aiAssistLevel === option.value}
                onChange={(e) => setFormData({ ...formData, aiAssistLevel: e.target.value })}
                className="h-4 w-4"
              />
              <span className="text-sm">{option.label}</span>
            </label>
          ))}
        </div>
      </div>
    </div>
  )
}

// 工具函数
function cn(...classes: string[]) {
  return classes.filter(Boolean).join(' ')
}
