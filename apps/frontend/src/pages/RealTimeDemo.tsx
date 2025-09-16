/**
 * SSE 实时事件演示页面
 * 展示如何在页面中集成 SSE 功能
 */

import React from 'react'
import { DashboardLayout } from '@/layouts/DashboardLayout'
import { RealTimeEvents } from '@/components/custom/RealTimeEvents'

export function RealTimeDemo() {
  return (
    <DashboardLayout>
      <div className="container mx-auto px-4 py-8">
        <RealTimeEvents />
      </div>
    </DashboardLayout>
  )
}

export default RealTimeDemo