import { createClient } from '@supabase/supabase-js'

import { env } from './env'

/** Shared browser Supabase client. Handles the session and auth for the SPA. */
export const supabase = createClient(env.supabaseUrl, env.supabaseAnonKey)

/** Current access token, or null when the user is signed out. */
export async function getAccessToken(): Promise<string | null> {
  const {
    data: { session },
  } = await supabase.auth.getSession()
  return session?.access_token ?? null
}