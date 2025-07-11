import { useState } from 'react'
import { User, Bell, Palette, Globe, Shield, HelpCircle } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

const settingsSections = [
  { id: 'profile', label: '个人资料', icon: User },
  { id: 'notifications', label: '通知设置', icon: Bell },
  { id: 'appearance', label: '外观设置', icon: Palette },
  { id: 'language', label: '语言设置', icon: Globe },
  { id: 'security', label: '安全设置', icon: Shield },
  { id: 'help', label: '帮助与支持', icon: HelpCircle },
]

export default function Settings() {
  const [activeSection, setActiveSection] = useState('profile')

  const renderContent = () => {
    switch (activeSection) {
      case 'profile':
        return <ProfileSettings />
      case 'notifications':
        return <NotificationSettings />
      case 'appearance':
        return <AppearanceSettings />
      case 'language':
        return <LanguageSettings />
      case 'security':
        return <SecuritySettings />
      case 'help':
        return <HelpSupport />
      default:
        return null
    }
  }

  return (
    <div className="container mx-auto py-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold">设置</h1>
        <p className="mt-2 text-muted-foreground">管理您的账户设置和偏好</p>
      </div>

      <div className="grid gap-6 md:grid-cols-[200px_1fr]">
        {/* 侧边导航 */}
        <nav className="space-y-1">
          {settingsSections.map((section) => {
            const Icon = section.icon
            return (
              <button
                key={section.id}
                onClick={() => setActiveSection(section.id)}
                className={cn(
                  'flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors',
                  'hover:bg-accent hover:text-accent-foreground',
                  activeSection === section.id && 'bg-accent text-accent-foreground font-medium',
                )}
              >
                <Icon className="h-4 w-4" />
                {section.label}
              </button>
            )
          })}
        </nav>

        {/* 内容区域 */}
        <div>{renderContent()}</div>
      </div>
    </div>
  )
}

// 个人资料设置
function ProfileSettings() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>个人资料</CardTitle>
        <CardDescription>更新您的个人信息</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <Label htmlFor="username">用户名</Label>
            <Input id="username" defaultValue="writer_2024" />
          </div>
          <div>
            <Label htmlFor="email">邮箱</Label>
            <Input id="email" type="email" defaultValue="writer@example.com" />
          </div>
        </div>
        <div>
          <Label htmlFor="bio">个人简介</Label>
          <textarea
            id="bio"
            className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            placeholder="介绍一下您自己..."
          />
        </div>
        <Button>保存更改</Button>
      </CardContent>
    </Card>
  )
}

// 通知设置
function NotificationSettings() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>通知设置</CardTitle>
        <CardDescription>管理您的通知偏好</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-4">
          {[
            {
              id: 'email',
              label: '邮件通知',
              description: '接收重要更新和提醒',
            },
            {
              id: 'browser',
              label: '浏览器通知',
              description: '在浏览器中接收实时通知',
            },
            {
              id: 'updates',
              label: '产品更新',
              description: '了解新功能和改进',
            },
          ].map((item) => (
            <div key={item.id} className="flex items-center justify-between">
              <div>
                <p className="font-medium">{item.label}</p>
                <p className="text-sm text-muted-foreground">{item.description}</p>
              </div>
              <label className="relative inline-flex cursor-pointer items-center">
                <input type="checkbox" className="peer sr-only" defaultChecked />
                <div className="peer h-6 w-11 rounded-full bg-gray-200 after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-gray-300 after:bg-white after:transition-all after:content-[''] peer-checked:bg-primary peer-checked:after:translate-x-full peer-checked:after:border-white peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/20"></div>
              </label>
            </div>
          ))}
        </div>
        <Button>保存设置</Button>
      </CardContent>
    </Card>
  )
}

// 外观设置
function AppearanceSettings() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>外观设置</CardTitle>
        <CardDescription>自定义应用的视觉效果</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <Label>主题</Label>
          <div className="mt-2 grid grid-cols-3 gap-2">
            {['浅色', '深色', '跟随系统'].map((theme) => (
              <button
                key={theme}
                className="rounded-lg border-2 border-muted bg-card p-3 text-center text-sm hover:border-primary"
              >
                {theme}
              </button>
            ))}
          </div>
        </div>
        <div>
          <Label htmlFor="fontSize">编辑器字体大小</Label>
          <Input id="fontSize" type="number" defaultValue="16" min="12" max="24" />
        </div>
        <Button>应用更改</Button>
      </CardContent>
    </Card>
  )
}

// 语言设置
function LanguageSettings() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>语言设置</CardTitle>
        <CardDescription>选择您的首选语言</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <Label>界面语言</Label>
          <select className="mt-2 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
            <option value="zh-CN">简体中文</option>
            <option value="zh-TW">繁体中文</option>
            <option value="en-US">English</option>
          </select>
        </div>
        <Button>保存设置</Button>
      </CardContent>
    </Card>
  )
}

// 安全设置
function SecuritySettings() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>安全设置</CardTitle>
        <CardDescription>保护您的账户安全</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-4">
          <div>
            <Label htmlFor="currentPassword">当前密码</Label>
            <Input id="currentPassword" type="password" />
          </div>
          <div>
            <Label htmlFor="newPassword">新密码</Label>
            <Input id="newPassword" type="password" />
          </div>
          <div>
            <Label htmlFor="confirmPassword">确认新密码</Label>
            <Input id="confirmPassword" type="password" />
          </div>
        </div>
        <Button>更新密码</Button>
      </CardContent>
    </Card>
  )
}

// 帮助与支持
function HelpSupport() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>帮助与支持</CardTitle>
        <CardDescription>获取帮助和联系支持团队</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <h3 className="font-medium">常见问题</h3>
          <ul className="space-y-1 text-sm text-muted-foreground">
            <li>• 如何开始创作新作品？</li>
            <li>• 如何使用 AI 辅助功能？</li>
            <li>• 如何导出我的作品？</li>
            <li>• 如何管理多个项目？</li>
          </ul>
        </div>
        <div className="space-y-2">
          <h3 className="font-medium">联系我们</h3>
          <p className="text-sm text-muted-foreground">
            如果您需要帮助，请发送邮件至 support@infinitescribe.com
          </p>
        </div>
        <Button variant="outline">查看帮助文档</Button>
      </CardContent>
    </Card>
  )
}
