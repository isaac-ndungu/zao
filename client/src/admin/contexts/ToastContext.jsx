/* eslint-disable react-refresh/only-export-components */
import { useCallback } from 'react'
import {
  ToastProvider as SharedToastProvider,
  useToast as useSharedToast,
} from '../../shared/components/ToastProvider'

export function ToastProvider({ children }) {
  return <SharedToastProvider>{children}</SharedToastProvider>
}

export function useToast() {
  const { toast } = useSharedToast()

  const showToast = useCallback(({ type = 'info', message, duration }) => {
    if (type === 'error') toast.error(message, duration)
    else if (type === 'success') toast.success(message, duration)
    else if (type === 'warning') toast.warning(message, duration)
    else toast.info(message, duration)
  }, [toast])

  return { showToast }
}
