/**
 * Unified frontend logger.
 * Use this instead of console.log for consistent logging behavior.
 * In production, non-error logs are suppressed.
 */
const isDev = import.meta.env.DEV

type LogFn = (...args: unknown[]) => void

interface Logger {
  debug: LogFn
  info: LogFn
  warn: LogFn
  error: LogFn
}

const noop = () => {}

export const logger: Logger = {
  debug: isDev ? (...args) => console.debug('[DEBUG]', ...args) : noop,
  info: isDev ? (...args) => console.info('[INFO]', ...args) : noop,
  warn: (...args) => console.warn('[WARN]', ...args),
  error: (...args) => console.error('[ERROR]', ...args),
}
