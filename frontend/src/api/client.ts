const BASE_URL = '/api/v1';

export class ApiError extends Error {
  status: number;
  detail: string;
  /** Field name (as sent to the API, e.g. "end_time") -> human-readable message. */
  fields: Record<string, string>;

  constructor(status: number, detail: string, fields: Record<string, string> = {}) {
    super(detail);
    this.status = status;
    this.detail = detail;
    this.fields = fields;
    this.name = 'ApiError';
  }
}

interface ValidationIssue {
  msg?: string;
  loc?: (string | number)[];
}

/** "end_time" -> "End time" */
export function humanizeField(field: string): string {
  const words = field.replace(/_/g, ' ');
  return words.charAt(0).toUpperCase() + words.slice(1);
}

/** Turn a FastAPI/Pydantic message into a sentence a user can read. */
function humanizeMessage(msg: string): string {
  const text = msg
    .replace(/^Value error, /, '')
    .replace(/\b[a-z]+(?:_[a-z]+)+\b/g, (f) => humanizeField(f).toLowerCase());
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function parseValidationIssues(issues: ValidationIssue[]): ApiError['fields'] & {
  __summary: string;
} {
  const fields: Record<string, string> = {};
  const lines: string[] = [];
  for (const issue of issues) {
    const message = humanizeMessage(issue.msg ?? 'Invalid value.');
    const field = (issue.loc ?? []).filter((part) => part !== 'body' && part !== 'query').pop();
    if (typeof field === 'string') {
      fields[field] ??= message;
      lines.push(`${humanizeField(field)}: ${message}`);
    } else {
      lines.push(message);
    }
  }
  return { ...fields, __summary: lines.join(' ') };
}

function getToken(): string | null {
  return localStorage.getItem('access_token');
}

export function setToken(token: string): void {
  localStorage.setItem('access_token', token);
}

export function clearToken(): void {
  localStorage.removeItem('access_token');
}

async function parseError(res: Response): Promise<ApiError> {
  let detail = res.statusText || 'Request failed.';
  let fields: Record<string, string> = {};
  try {
    const body = await res.json();
    if (typeof body.detail === 'string') {
      detail = body.detail;
    } else if (Array.isArray(body.detail)) {
      const { __summary, ...parsed } = parseValidationIssues(body.detail);
      detail = __summary || 'Please check the highlighted fields.';
      fields = parsed;
    }
  } catch {
    // body is not JSON
  }
  if (res.status >= 500) {
    detail = 'Something went wrong on the server. Please try again in a moment.';
  }
  return new ApiError(res.status, detail, fields);
}

export async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  auth = true,
): Promise<T> {
  const headers: Record<string, string> = {};
  if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
  }
  if (auth) {
    const token = getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
  }
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, 'Cannot reach the server. Check your connection and try again.');
  }
  if (!res.ok) {
    if (res.status === 401 && auth) {
      clearToken();
      window.dispatchEvent(new Event('auth:unauthorized'));
    }
    throw await parseError(res);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return res.json() as Promise<T>;
}

export async function requestBlob(
  method: string,
  path: string,
): Promise<Blob> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  const res = await fetch(`${BASE_URL}${path}`, { method, headers });
  if (!res.ok) {
    if (res.status === 401) {
      clearToken();
      window.dispatchEvent(new Event('auth:unauthorized'));
    }
    throw await parseError(res);
  }
  return res.blob();
}
