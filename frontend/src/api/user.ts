import {
  usersList,
  usersCreate,
  usersUpdate,
  usersDeactivateCreate,
  usersActivateCreate
} from './generated/sdk.gen'
import type {
  UserListOutput,
  UserCreateInputWritable,
  UserUpdateInputWritable
} from './generated/types.gen'

export type { UserListOutput, UserCreateInputWritable, UserUpdateInputWritable }

function extractErrorMessage(error: unknown, fallback: string): string {
  if (typeof error === 'object' && error !== null) {
    const errObj = error as Record<string, unknown>
    if (typeof errObj.detail === 'string') return errObj.detail
    if (typeof errObj.message === 'string') return errObj.message
    const firstKey = Object.keys(errObj)[0]
    if (firstKey !== undefined) {
      const firstVal = errObj[firstKey]
      if (Array.isArray(firstVal) && firstVal.length > 0 && typeof firstVal[0] === 'string') {
        return `${firstKey}: ${firstVal[0]}`
      }
    }
  }
  return fallback
}

export async function fetchUsers(): Promise<UserListOutput[]> {
  const res = await usersList()
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to fetch users'))
  }
  return res.data ?? []
}

export async function createUser(body: UserCreateInputWritable): Promise<UserListOutput> {
  const res = await usersCreate({ body })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to create user'))
  }
  if (!res.data) {
    throw new Error('No data returned from user creation')
  }
  return res.data
}

export async function updateUser(
  id: number,
  body: UserUpdateInputWritable
): Promise<UserListOutput> {
  const res = await usersUpdate({
    path: { id },
    body
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to update user'))
  }
  if (!res.data) {
    throw new Error('No data returned from user update')
  }
  return res.data
}

export async function deactivateUser(id: number): Promise<UserListOutput> {
  const res = await usersDeactivateCreate({
    path: { id }
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to deactivate user'))
  }
  if (!res.data) {
    throw new Error('No data returned from user deactivation')
  }
  return res.data
}

export async function activateUser(id: number): Promise<UserListOutput> {
  const res = await usersActivateCreate({
    path: { id }
  })
  if (res.error) {
    throw new Error(extractErrorMessage(res.error, 'Failed to activate user'))
  }
  if (!res.data) {
    throw new Error('No data returned from user activation')
  }
  return res.data
}
