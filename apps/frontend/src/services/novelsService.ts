/**
 * 小说管理API客户端服务
 * 实现所有小说相关的API调用
 */

import { authenticatedApiService } from './authenticatedApiService'
import type {
  Novel,
  Character,
  Chapter,
  CreateNovelRequest,
  UpdateNovelRequest,
  NovelQueryParams,
  ApiResponse,
  PaginatedApiResponse,
} from '@/types/api'
import type { NovelStats } from '@/types/api'

/**
 * 处理API响应的辅助函数
 */
function handleApiResponse<T>(response: ApiResponse<T>): T {
  if (response.code === 0) {
    return response.data as T
  } else {
    throw new Error(response.msg || 'API请求失败')
  }
}

export class NovelsService {
  /**
   * 获取用户的小说列表
   * GET /api/v1/novels
   */
  async getNovels(params?: NovelQueryParams): Promise<{ items: Novel[], pagination: any }> {
    const searchParams = new URLSearchParams()
    
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          if (Array.isArray(value)) {
            value.forEach(v => searchParams.append(key, v.toString()))
          } else {
            searchParams.append(key, value.toString())
          }
        }
      })
    }

    const query = searchParams.toString()
    const url = query ? `/api/v1/novels?${query}` : '/api/v1/novels'
    
    const response = await authenticatedApiService.get<PaginatedApiResponse<Novel>>(url)
    return handleApiResponse(response)
  }

  /**
   * 创建新小说
   * POST /api/v1/novels
   */
  async createNovel(novel: CreateNovelRequest): Promise<Novel> {
    const response = await authenticatedApiService.post<ApiResponse<Novel>>('/api/v1/novels', novel)
    return handleApiResponse(response)
  }

  /**
   * 获取小说详情
   * GET /api/v1/novels/{id}
   */
  async getNovel(id: string): Promise<Novel> {
    const response = await authenticatedApiService.get<ApiResponse<Novel>>(`/api/v1/novels/${id}`)
    return handleApiResponse(response)
  }

  /**
   * 更新小说信息
   * PUT /api/v1/novels/{id}
   */
  async updateNovel(id: string, updates: UpdateNovelRequest): Promise<Novel> {
    const response = await authenticatedApiService.put<ApiResponse<Novel>>(`/api/v1/novels/${id}`, updates)
    return handleApiResponse(response)
  }

  /**
   * 删除小说
   * DELETE /api/v1/novels/{id}
   */
  async deleteNovel(id: string): Promise<void> {
    const response = await authenticatedApiService.delete<ApiResponse<null>>(`/api/v1/novels/${id}`)
    handleApiResponse(response)
  }

  /**
   * 获取小说的章节列表
   * GET /api/v1/novels/{id}/chapters
   */
  async getNovelChapters(novelId: string): Promise<Chapter[]> {
    const response = await authenticatedApiService.get<ApiResponse<Chapter[]>>(`/api/v1/novels/${novelId}/chapters`)
    return handleApiResponse(response)
  }

  /**
   * 获取小说的角色列表
   * GET /api/v1/novels/{id}/characters
   */
  async getNovelCharacters(novelId: string): Promise<Character[]> {
    const response = await authenticatedApiService.get<ApiResponse<Character[]>>(`/api/v1/novels/${novelId}/characters`)
    return handleApiResponse(response)
  }

  /**
   * 获取小说统计信息
   * GET /api/v1/novels/{id}/stats
   */
  async getNovelStats(novelId: string): Promise<NovelStats> {
    const response = await authenticatedApiService.get<ApiResponse<NovelStats>>(`/api/v1/novels/${novelId}/stats`)
    return handleApiResponse(response)
  }
}

// 导出单例实例
export const novelsService = new NovelsService()