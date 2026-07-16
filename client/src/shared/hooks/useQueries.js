import { useQuery } from '../api/queryProvider'
import { createQueryFn } from '../api/queryFn'
import { apiFetch } from '../api/client'

const queryFn = createQueryFn(apiFetch)

export function useFarmerProfile() {
  return useQuery({
    queryKey: ['/api/farmers/me/'],
    queryFn,
    staleTime: 60 * 1000,
  })
}

export function useCooperative() {
  return useQuery({
    queryKey: ['/api/cooperatives/me/'],
    queryFn,
    staleTime: 60 * 1000,
  })
}

export function useDeliveries({ page = 1, pageSize = 20, ordering = '-date_delivered', enabled = true } = {}) {
  return useQuery({
    queryKey: ['/api/deliveries/', { page, page_size: pageSize, ordering }],
    queryFn,
    enabled,
  })
}

export function useLoans({ status, enabled = true } = {}) {
  const params = status ? { status } : {}
  return useQuery({
    queryKey: ['/api/loans/', params],
    queryFn,
    enabled,
  })
}

export function useDashboard({ period } = {}) {
  return useQuery({
    queryKey: ['/api/analytics/dashboard/', period ? { period } : {}],
    queryFn,
    staleTime: 30 * 1000,
  })
}

export function useFinancial({ period } = {}) {
  return useQuery({
    queryKey: ['/api/analytics/financial/', period ? { period } : {}],
    queryFn,
    staleTime: 30 * 1000,
  })
}
