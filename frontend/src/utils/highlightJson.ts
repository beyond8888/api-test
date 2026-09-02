/**
 * Simple JSON syntax highlighter that returns HTML with colored spans.
 * Uses a single-pass tokenizer for strings, numbers, booleans, null, keys, and punctuation.
 */
export function highlightJson(json: string): string {
  if (!json) return ''

  // If it's already HTML (not raw JSON), return as-is
  if (/<\/?[a-z][\s\S]*>/i.test(json.trim().slice(0, 20))) return json

  // Escape HTML first
  const escaped = json
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  return escaped.replace(
    /("(?:\\.|[^"\\])*"\s*:)|("(?:\\.|[^"\\])*")|(-?\d+\.?\d*(?:[eE][+-]?\d+)?)|(true|false)|(null)|([{}[\],:]|\b(?:undefined|NaN|Infinity)\b)/g,
    (match, key, str, num, bool, nil, punct) => {
      if (key) return `<span class="json-key">${key}</span>`
      if (str) return `<span class="json-string">${str}</span>`
      if (num) return `<span class="json-number">${num}</span>`
      if (bool) return `<span class="json-bool">${bool}</span>`
      if (nil) return `<span class="json-null">${nil}</span>`
      return `<span class="json-punct">${punct}</span>`
    },
  )
}
