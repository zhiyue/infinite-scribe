/**
 * 自定义 RJSF Widgets
 * 使用 shadcn/ui 组件来保持视觉一致性
 */

import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'
import type {
  ArrayFieldTemplateProps,
  FieldTemplateProps,
  ObjectFieldTemplateProps,
  WidgetProps,
} from '@rjsf/utils'
import { AlertCircle, Minus, Plus, ArrowUp, ArrowDown } from 'lucide-react'

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
  options,
}: WidgetProps) {
  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChange(event.target.value === '' ? options.emptyValue : event.target.value)
  }

  const handleFocus = (event: React.FocusEvent<HTMLInputElement>) => {
    if (onFocus) onFocus(id, event.target.value)
  }

  const handleBlur = (event: React.FocusEvent<HTMLInputElement>) => {
    if (onBlur) onBlur(id, event.target.value)
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
      onFocus={handleFocus}
      onBlur={handleBlur}
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

  const handleFocus = (event: React.FocusEvent<HTMLTextAreaElement>) => {
    if (onFocus) onFocus(id, event.target.value)
  }

  const handleBlur = (event: React.FocusEvent<HTMLTextAreaElement>) => {
    if (onBlur) onBlur(id, event.target.value)
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
      onFocus={handleFocus}
      onBlur={handleBlur}
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

  const handleFocus = (event: React.FocusEvent<HTMLInputElement>) => {
    if (onFocus) onFocus(id, event.target.value)
  }

  const handleBlur = (event: React.FocusEvent<HTMLInputElement>) => {
    if (onBlur) onBlur(id, event.target.value)
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
      onFocus={handleFocus}
      onBlur={handleBlur}
      min={schema?.minimum}
      max={schema?.maximum}
      step={schema?.multipleOf || 1}
      className="w-full"
    />
  )
}

/**
 * 选择框 Widget
 */
export function SelectWidget({
  id,
  readonly,
  disabled,
  value,
  onChange,
  options,
  placeholder,
}: WidgetProps) {
  const { enumOptions = [] } = options

  return (
    <Select value={value || ''} onValueChange={onChange} disabled={disabled || readonly}>
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
export function CheckboxWidget({ id, value, disabled, readonly, onChange, label }: WidgetProps) {
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
 * 数组字段模板 - 优化的列表布局
 */
export function ArrayFieldTemplate({
  items,
  onAddClick,
  canAdd,
  uiSchema,
  disabled,
  readonly,
}: ArrayFieldTemplateProps) {
  const uiOptions = uiSchema?.['ui:options'] || {}
  const orderable = uiOptions.orderable !== false
  const addable = uiOptions.addable !== false && canAdd
  const removable = uiOptions.removable !== false
  const baseAddText = uiOptions.addButtonText as string | undefined
  const addButtonText = baseAddText
    ? items.length === 0
      ? baseAddText
      : `继续${baseAddText}`
    : items.length === 0
      ? '添加项目'
      : '添加更多'
  const itemTitle = uiOptions.itemTitle as string | undefined
  const maxListHeight = uiOptions.maxListHeight as number | undefined

  return (
    <div className="space-y-3">
      <div
        className={cn('space-y-3', maxListHeight ? 'overflow-y-auto pr-1' : '')}
        style={maxListHeight ? { maxHeight: `${maxListHeight}px` } : undefined}
      >
        {items.map((item, index) => {
          const dynamicTitle = (item.children?.props as any)?.schema?.title as string | undefined
          const finalTitle = dynamicTitle || itemTitle

          return (
            <div
              key={item.key}
              className="array-item rounded-lg border border-border/50 bg-muted/20 px-4 py-3 shadow-sm"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2 text-xs text-muted-foreground select-none">
                  <Badge variant="outline" className="border-border/60 bg-background/90 px-1.5 py-0 text-[11px] font-medium">
                    #{index + 1}
                  </Badge>
                  {finalTitle && (
                    <span className="text-sm font-medium text-foreground/80">
                      {finalTitle}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-1">
                  {orderable && (
                    <div className="flex items-center gap-1 text-muted-foreground">
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={item.onReorderClick(index, index - 1)}
                        disabled={disabled || readonly || !item.hasMoveUp}
                        aria-label={`上移${finalTitle ?? '项目'}${index + 1}`}
                      >
                        <ArrowUp className="h-4 w-4" />
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={item.onReorderClick(index, index + 1)}
                        disabled={disabled || readonly || !item.hasMoveDown}
                        aria-label={`下移${finalTitle ?? '项目'}${index + 1}`}
                      >
                        <ArrowDown className="h-4 w-4" />
                      </Button>
                    </div>
                  )}
                  {removable && item.hasRemove && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={item.onDropIndexClick(index)}
                      disabled={disabled || readonly}
                      className="h-7 w-7 text-destructive hover:bg-destructive/10"
                      aria-label={`删除${finalTitle ?? '项目'}${index + 1}`}
                    >
                      <Minus className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              </div>
              <div className="mt-3">
                {item.children}
              </div>
            </div>
          )
        })}
      </div>

      {addable && (
        <div className="flex justify-center pt-0.5">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onAddClick}
            disabled={disabled || readonly}
            className="gap-2"
          >
            <Plus className="h-4 w-4" />
            {addButtonText}
          </Button>
        </div>
      )}
    </div>
  )
}

/**
 * 对象字段模板 - 简化版，不显示重复标题
 */
export function ObjectFieldTemplate({ properties }: ObjectFieldTemplateProps) {
  return (
    <div className="space-y-4">
      {properties.map((prop, index) => (
        <div key={prop.name}>
          {prop.content}
          {index < properties.length - 1 && <Separator className="my-4" />}
        </div>
      ))}
    </div>
  )
}

/**
 * 字段模板 - 优化为行内布局
 */
export function FieldTemplate({
  id,
  label,
  help,
  required,
  description,
  errors,
  children,
  displayLabel,
}: FieldTemplateProps) {
  const showLabel = displayLabel && label
  const errorList = Array.isArray(errors) ? errors : []
  const hasErrors = errorList.length > 0

  return (
    <div className="space-y-2">
      <div className="flex flex-col gap-2 md:flex-row md:gap-6">
        {showLabel && (
          <div className="md:w-48 md:min-w-[12rem] select-none">
            <Label className="text-sm font-medium cursor-default select-none pointer-events-none">
              {label}
              {required && <span className="text-destructive ml-1">*</span>}
            </Label>
            {description && (
              <p className="text-xs text-muted-foreground mt-1 leading-4 select-none cursor-default">
                {description}
              </p>
            )}
          </div>
        )}

        <div className="flex-1 space-y-2">
          {children}

          {hasErrors && (
            <Alert variant="destructive" className="py-2">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription className="text-sm">
                {errorList
                  .map((error) => (typeof error === 'string' ? error : String(error)))
                  .join(', ')}
              </AlertDescription>
            </Alert>
          )}

          {help && <p className="text-xs text-muted-foreground cursor-default select-none">{help}</p>}
        </div>
      </div>
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
