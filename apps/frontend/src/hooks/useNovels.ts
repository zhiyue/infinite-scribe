/**
 * 小说管理相关的TanStack Query hooks
 */

import { novelsService } from '@/services/novelsService'
import type { CreateNovelRequest, NovelQueryParams, UpdateNovelRequest } from '@/types/api'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

// Query Keys
export const novelKeys = {
  all: ['novels'] as const,
  lists: () => [...novelKeys.all, 'list'] as const,
  list: (params?: NovelQueryParams) => [...novelKeys.lists(), params] as const,
  details: () => [...novelKeys.all, 'detail'] as const,
  detail: (id: string) => [...novelKeys.details(), id] as const,
  chapters: (novelId: string) => [...novelKeys.detail(novelId), 'chapters'] as const,
  characters: (novelId: string) => [...novelKeys.detail(novelId), 'characters'] as const,
  stats: (novelId: string) => [...novelKeys.detail(novelId), 'stats'] as const,
}

// Query Hooks

/**
 * 获取小说列表
 */
export function useNovels(params?: NovelQueryParams) {
  return useQuery({
    queryKey: novelKeys.list(params),
    queryFn: () => novelsService.getNovels(params),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

/**
 * 获取单个小说详情
 */
export function useNovel(id: string) {
  return useQuery({
    queryKey: novelKeys.detail(id),
    queryFn: () => novelsService.getNovel(id),
    enabled: !!id,
    staleTime: 10 * 60 * 1000, // 10 minutes
  })
}

/**
 * 获取小说章节列表
 */
export function useNovelChapters(novelId: string) {
  return useQuery({
    queryKey: novelKeys.chapters(novelId),
    queryFn: () => novelsService.getNovelChapters(novelId),
    enabled: !!novelId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

/**
 * 获取小说角色列表
 */
export function useNovelCharacters(novelId: string) {
  return useQuery({
    queryKey: novelKeys.characters(novelId),
    queryFn: () => novelsService.getNovelCharacters(novelId),
    enabled: !!novelId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

/**
 * 获取小说统计信息
 */
export function useNovelStats(novelId: string) {
  return useQuery({
    queryKey: novelKeys.stats(novelId),
    queryFn: () => novelsService.getNovelStats(novelId),
    enabled: !!novelId,
    staleTime: 2 * 60 * 1000, // 2 minutes
  })
}

// Mutation Hooks

/**
 * 创建小说
 */
export function useCreateNovel() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (novel: CreateNovelRequest) => novelsService.createNovel(novel),
    onSuccess: (newNovel) => {
      // 清除所有小说列表相关的缓存，包括带参数的查询
      queryClient.invalidateQueries({
        queryKey: novelKeys.lists(),
        exact: false, // 这样会匹配所有以 ['novels', 'list'] 开头的查询键
      })

      // 添加新小说到缓存
      queryClient.setQueryData(novelKeys.detail(newNovel.id), newNovel)
    },
  })
}

/**
 * 更新小说
 */
export function useUpdateNovel(id: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (updates: UpdateNovelRequest) => novelsService.updateNovel(id, updates),
    onSuccess: (updatedNovel) => {
      // 更新特定小说缓存
      queryClient.setQueryData(novelKeys.detail(id), updatedNovel)

      // 清除相关的列表缓存
      queryClient.invalidateQueries({ queryKey: novelKeys.lists(), exact: false })
    },
  })
}

/**
 * 删除小说
 */
export function useDeleteNovel() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => novelsService.deleteNovel(id),
    onSuccess: (_, deletedId) => {
      // 从缓存中移除已删除的小说
      queryClient.removeQueries({ queryKey: novelKeys.detail(deletedId) })

      // 清除相关的列表和子资源缓存
      queryClient.invalidateQueries({ queryKey: novelKeys.lists(), exact: false })
      queryClient.removeQueries({ queryKey: novelKeys.chapters(deletedId) })
      queryClient.removeQueries({ queryKey: novelKeys.characters(deletedId) })
      queryClient.removeQueries({ queryKey: novelKeys.stats(deletedId) })
    },
  })
}

// Utility hooks

/**
 * 预加载小说详情
 */
export function usePrefetchNovel() {
  const queryClient = useQueryClient()

  return (id: string) => {
    queryClient.prefetchQuery({
      queryKey: novelKeys.detail(id),
      queryFn: () => novelsService.getNovel(id),
      staleTime: 10 * 60 * 1000, // 10 minutes
    })
  }
}
