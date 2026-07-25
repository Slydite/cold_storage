import { useQuery, useMutation, useQueryClient } from '@tanstack/vue-query'
import {
  fetchUsers,
  createUser,
  updateUser,
  deactivateUser,
  activateUser
} from '../api/user'
import type { UserCreateInputWritable, UserUpdateInputWritable } from '../api/user'

export function useUserList() {
  return useQuery({
    queryKey: ['users'],
    queryFn: () => fetchUsers()
  })
}

export function useCreateUser() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: UserCreateInputWritable) => createUser(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
    }
  })
}

export function useUpdateUser() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: UserUpdateInputWritable }) =>
      updateUser(id, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
    }
  })
}

export function useDeactivateUser() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => deactivateUser(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
    }
  })
}

export function useActivateUser() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => activateUser(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
    }
  })
}
