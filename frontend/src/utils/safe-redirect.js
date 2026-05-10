/**
 * Restrict a `?redirect=` query value to same-origin relative paths.
 *
 * Without this, `?redirect=https://evil.example` could navigate users
 * off-site after a successful login (open-redirect). Surfaced in the
 * 2026-05-10 multi-user-auth-core code review.
 *
 * Returns `/chat` (the default landing page) for any input that is not
 * a clean relative path starting with a single `/`.
 */
export function safeRedirect(raw) {
  if (typeof raw !== 'string' || raw.length === 0) return '/chat'
  // Reject protocol-relative (//host/...) URLs.
  if (raw.startsWith('//')) return '/chat'
  // Reject any scheme: prefix (http:, https:, javascript:, data:, etc.).
  if (/^[a-z][a-z0-9+.-]*:/i.test(raw)) return '/chat'
  // Must be a clean relative path starting with /.
  if (!raw.startsWith('/')) return '/chat'
  return raw
}
