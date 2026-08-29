/**
 * Validated runtime env. The single place that reads `import.meta.env`.
 * Importing this module throws at boot when a required var is missing, so the
 * app fails fast instead of half-working with an empty config.
 */

function requireEnv(name: string): string {
  const value = import.meta.env[name]
  if (typeof value !== 'string' || value.length === 0) {
    throw new Error(`Missing required env var: ${name}`)
  }
  return value
}

export const env = {
  apiBaseUrl: import.meta.env['VITE_API_BASE_URL'] ?? '',
  supabaseUrl: requireEnv('VITE_SUPABASE_URL'),
  supabaseAnonKey: requireEnv('VITE_SUPABASE_ANON_KEY'),
}