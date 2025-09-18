/**
 * 自定义 RJSF Widgets
 * 使用 shadcn/ui 组件来保持视觉一致性
 */

import type {
  WidgetProps,
  ArrayFieldTemplateProps,
  ObjectFieldTemplateProps,
  FieldTemplateProps,
} from '@rjsf/utils'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Switch } from '@/components/ui/switch'
import { Separator } from '@/components/ui/separator'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Plus,
  Minus,
  GripVertical,
  AlertCircle,
} from 'lucide-react'

/**
 * 文本输入框 Widget
 */
export function TextWidget({
  id,
  placeholder,
  required,
  readonly,
  disabled,
  value,
  onChange,
  onFocus,
  onBlur,
  schema,
  options,
}: WidgetProps) {
  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChange(event.target.value === '' ? options.emptyValue : event.target.value)
  }

  return (
    <Input
      id={id}
      placeholder={placeholder}
      required={required}
      readOnly={readonly}
      disabled={disabled}
      value={value || ''}
      onChange={handleChange}
      onFocus={onFocus}
      onBlur={onBlur}
      className="w-full"
    />
  )
}

/**
 * 多行文本输入框 Widget
 */
export function TextareaWidget({
  id,
  placeholder,
  required,
  readonly,
  disabled,
  value,
  onChange,
  onFocus,
  onBlur,
  options,
}: WidgetProps) {
  const handleChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    onChange(event.target.value === '' ? options.emptyValue : event.target.value)
  }

  return (
    <Textarea
      id={id}
      placeholder={placeholder}
      required={required}
      readOnly={readonly}
      disabled={disabled}
      value={value || ''}
      onChange={handleChange}
      onFocus={onFocus}
      onBlur={onBlur}
      className="w-full min-h-[100px]"
      rows={4}
    />
  )
}

/**
 * 数字输入框 Widget
 */
export function NumberWidget({
  id,
  placeholder,
  required,
  readonly,
  disabled,
  value,
  onChange,
  onFocus,
  onBlur,
  schema,
  options,
}: WidgetProps) {
  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = event.target.value
    onChange(newValue === '' ? options.emptyValue : Number(newValue))
  }

  return (
    <Input
      id={id}
      type="number"
      placeholder={placeholder}
      required={required}
      readOnly={readonly}
      disabled={disabled}
      value={value ?? ''}
      onChange={handleChange}
      onFocus={onFocus}
      onBlur={onBlur}
      min={schema.minimum}
      max={schema.maximum}
      step={schema.multipleOf || 1}
      className="w-full"
    />
  )
}

/**
 * 选择框 Widget
 */
export function SelectWidget({
  id,
  required,
  readonly,
  disabled,
  value,
  onChange,
  options,
  placeholder,
}: WidgetProps) {
  const { enumOptions = [] } = options

  return (
    <Select
      value={value || ''}
      onValueChange={onChange}
      disabled={disabled || readonly}
    >
      <SelectTrigger id={id} className="w-full">
        <SelectValue placeholder={placeholder || '请选择...'} />
      </SelectTrigger>
      <SelectContent>
        {enumOptions.map((option: any) => (
          <SelectItem key={option.value} value={option.value}>
            {option.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}

/**
 * 布尔值开关 Widget
 */
export function CheckboxWidget({
  id,
  value,
  required,
  disabled,
  readonly,
  onChange,
  label,
}: WidgetProps) {
  return (
    <div className="flex items-center space-x-2">
      <Switch
        id={id}
        checked={value || false}
        onCheckedChange={onChange}
        disabled={disabled || readonly}
      />
      {label && (
        <Label htmlFor={id} className="text-sm font-medium">
          {label}
        </Label>
      )}
    </div>
  )
}

/**
 * 数组字段模板
 */
export function ArrayFieldTemplate({
  items,
  onAddClick,
  canAdd,
  title,
  schema,
  uiSchema,
  disabled,
  readonly,
}: ArrayFieldTemplateProps) {
  const uiOptions = uiSchema?.['ui:options'] || {}
  const orderable = uiOptions.orderable !== false
  const addable = uiOptions.addable !== false && canAdd
  const removable = uiOptions.removable !== false

  return (
    <div className="space-y-4">
      {title && (
        <div className="flex items-center justify-between">
          <Label className="text-sm font-medium">{title}</Label>
          {addable && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onAddClick}
              disabled={disabled || readonly}
              className="gap-2"
            >
              <Plus className="h-4 w-4" />
              添加项目
            </Button>
          )}
        </div>
      )}

      <div className="space-y-3">
        {items.map((item, index) => (
          <Card key={item.key} className="relative">
            <CardContent className="p-4">
              <div className="flex items-start gap-3">
                {orderable && (
                  <div className="flex flex-col gap-1 mt-2">
                    <GripVertical className="h-4 w-4 text-muted-foreground cursor-move" />
                  </div>
                )}

                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-3">
                    <Badge variant="secondary" className="text-xs">
                      项目 {index + 1}
                    </Badge>
                  </div>
                  {item.children}
                </div>

                {removable && item.hasRemove && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={item.onDropIndexClick(index)}
                    disabled={disabled || readonly}
                    className="text-destructive hover:text-destructive"
                  >
                    <Minus className="h-4 w-4" />
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        ))}

        {items.length === 0 && (
          <div className="text-center py-8 text-muted-foreground">
            <p className="text-sm">暂无项目</p>
            {addable && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={onAddClick}
                disabled={disabled || readonly}
                className="mt-3 gap-2"
              >
                <Plus className="h-4 w-4" />
                添加第一个项目
              </Button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * 对象字段模板
 */
export function ObjectFieldTemplate({
  title,
  description,
  properties,
  required,
  disabled,
  readonly,
}: ObjectFieldTemplateProps) {
  return (
    <div className="space-y-6">
      {title && (
        <div>
          <h3 className="text-lg font-medium">{title}</h3>
          {description && (
            <p className="text-sm text-muted-foreground mt-1">{description}</p>
          )}
        </div>
      )}

      <div className="space-y-4">
        {properties.map((prop, index) => (
          <div key={prop.name} className="space-y-2">
            {prop.content}
            {index < properties.length - 1 && <Separator className="my-4" />}
          </div>
        ))}
      </div>
    </div>
  )
}

/**
 * 字段模板
 */
export function FieldTemplate({
  id,
  label,
  help,
  required,
  description,
  errors,
  children,
  schema,
  displayLabel,
}: FieldTemplateProps) {
  const showLabel = displayLabel && label
  const errorList = Array.isArray(errors) ? errors : []
  const hasErrors = errorList.length > 0

  return (
    <div className="space-y-2">
      {showLabel && (
        <Label htmlFor={id} className="text-sm font-medium">
          {label}
          {required && <span className="text-destructive ml-1">*</span>}
        </Label>
      )}

      {description && (
        <p className="text-sm text-muted-foreground">{description}</p>
      )}

      <div>{children}</div>

      {hasErrors && (
        <Alert variant="destructive" className="py-2">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription className="text-sm">
            {errorList.map(error => typeof error === 'string' ? error : String(error)).join(', ')}
          </AlertDescription>
        </Alert>
      )}

      {help && (
        <p className="text-xs text-muted-foreground">{help}</p>
      )}
    </div>
  )
}

/**
 * Widget 映射
 */
export const customWidgets = {
  TextWidget,
  TextareaWidget,
  NumberWidget,
  SelectWidget,
  CheckboxWidget,
}

/**
 * 模板映射
 */
export const customTemplates = {
  ArrayFieldTemplate,
  ObjectFieldTemplate,
  FieldTemplate,
}

/**
 * 完整的自定义主题
 */
export const customTheme = {
  widgets: customWidgets,
  templates: customTemplates,
}