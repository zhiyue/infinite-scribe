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
  ChaptersResponse,
  CharactersResponse,
  NovelStatsResponse,
} from '@/types/api'

export class NovelsService {
  /**
   * 获取用户的小说列表
   * GET /api/v1/novels
   */
  async getNovels(params?: NovelQueryParams): Promise<Novel[]> {
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
    
    return authenticatedApiService.get<Novel[]>(url)
  }

  /**
   * 创建新小说
   * POST /api/v1/novels
   */
  async createNovel(novel: CreateNovelRequest): Promise<Novel> {
    return authenticatedApiService.post<Novel>('/api/v1/novels', novel)
  }

  /**
   * 获取小说详情
   * GET /api/v1/novels/{id}
   */
  async getNovel(id: string): Promise<Novel> {
    return authenticatedApiService.get<Novel>(`/api/v1/novels/${id}`)
  }

  /**
   * 更新小说信息
   * PUT /api/v1/novels/{id}
   */
  async updateNovel(id: string, updates: UpdateNovelRequest): Promise<Novel> {
    return authenticatedApiService.put<Novel>(`/api/v1/novels/${id}`, updates)
  }

  /**
   * 删除小说
   * DELETE /api/v1/novels/{id}
   */
  async deleteNovel(id: string): Promise<void> {
    return authenticatedApiService.delete<void>(`/api/v1/novels/${id}`)
  }

  /**
   * 获取小说的章节列表
   * GET /api/v1/novels/{id}/chapters
   */
  async getNovelChapters(novelId: string): Promise<ChaptersResponse> {
    return authenticatedApiService.get<ChaptersResponse>(`/api/v1/novels/${novelId}/chapters`)
  }

  /**
   * 获取小说的角色列表
   * GET /api/v1/novels/{id}/characters
   */
  async getNovelCharacters(novelId: string): Promise<CharactersResponse> {
    return authenticatedApiService.get<CharactersResponse>(`/api/v1/novels/${novelId}/characters`)
  }

  /**
   * 获取小说统计信息
   * GET /api/v1/novels/{id}/stats
   */
  async getNovelStats(novelId: string): Promise<NovelStatsResponse> {
    return authenticatedApiService.get<NovelStatsResponse>(`/api/v1/novels/${novelId}/stats`)
  }
}

// 导出单例实例
export const novelsService = new NovelsService()