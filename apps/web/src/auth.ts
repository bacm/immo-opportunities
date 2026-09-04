import { UserManager, WebStorageStateStore, type User } from 'oidc-client-ts'

const disabled = import.meta.env.DEV || import.meta.env.VITE_AUTH_DISABLED === 'true'
const authority = import.meta.env.VITE_OIDC_AUTHORITY
  ?? `${window.location.origin}/auth/realms/immo`

const manager = disabled ? null : new UserManager({
  authority,
  client_id: import.meta.env.VITE_OIDC_CLIENT_ID ?? 'immo-web',
  redirect_uri: window.location.origin + window.location.pathname,
  post_logout_redirect_uri: window.location.origin,
  response_type: 'code',
  scope: 'openid profile email offline_access',
  automaticSilentRenew: true,
  monitorSession: true,
  userStore: new WebStorageStateStore({ store: window.sessionStorage }),
})

let currentUser: User | null = null

export async function initializeAuth(): Promise<void> {
  if (!manager) return
  if (new URLSearchParams(window.location.search).has('code')) {
    currentUser = await manager.signinRedirectCallback()
    const returnTo = (currentUser.state as { returnTo?: unknown } | undefined)?.returnTo
    const target = typeof returnTo === 'string' ? new URL(returnTo, window.location.origin) : null
    window.history.replaceState(
      null,
      '',
      target?.origin === window.location.origin
        ? `${target.pathname}${target.search}${target.hash}`
        : window.location.pathname,
    )
  } else {
    currentUser = await manager.getUser()
  }
  if (!currentUser || currentUser.expired) {
    await manager.signinRedirect({ state: { returnTo: window.location.href } })
    return new Promise(() => undefined)
  }
  manager.events.addAccessTokenExpired(() => {
    void manager.signinRedirect({ state: { returnTo: window.location.href } })
  })
  manager.events.addUserLoaded((user) => { currentUser = user })
  manager.events.addSilentRenewError(() => {
    void manager.signinRedirect({ state: { returnTo: window.location.href } })
  })
}

export function getAccessToken(): string | null {
  return currentUser?.access_token ?? null
}

export async function signOut(): Promise<void> {
  await manager?.signoutRedirect()
}
