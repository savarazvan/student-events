/**
 * Client-side validation mirroring the backend rules, so users get a clear
 * message next to the field before the request is sent.
 */

export type FieldErrors<K extends string = string> = Partial<Record<K, string>>;

/** Same rules as the backend's e-mail normalizer (app/schemas/auth.py). */
export function emailError(value: string, required = true): string | undefined {
  const email = value.trim().toLowerCase();
  if (!email) return required ? 'Enter your e-mail address.' : undefined;
  const at = email.indexOf('@');
  const local = email.slice(0, at);
  const domain = email.slice(at + 1);
  if (
    at <= 0 ||
    !domain ||
    domain.includes('@') ||
    !domain.includes('.') ||
    /\s/.test(email) ||
    domain.startsWith('.') ||
    domain.endsWith('.') ||
    domain.includes('..') ||
    !local
  ) {
    return 'Enter a valid e-mail address, e.g. name@stud.ubbcluj.ro.';
  }
  if (email.length > 320) return 'E-mail address is too long.';
  return undefined;
}

export function passwordError(value: string, forRegistration: boolean): string | undefined {
  if (!value) return 'Enter your password.';
  if (!forRegistration) return undefined;
  if (value.length < 8) return 'Password must have at least 8 characters.';
  if (new TextEncoder().encode(value).length > 72) return 'Password is too long (max 72 bytes).';
  return undefined;
}

export function requiredText(value: string, label: string, max = 255): string | undefined {
  if (!value.trim()) return `${label} is required.`;
  if (value.trim().length > max) return `${label} must have at most ${max} characters.`;
  return undefined;
}

const IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.webp'];

/** Backend accepts absolute http(s) URLs ending in an image extension. */
export function imageUrlError(value: string): string | undefined {
  if (!value.trim()) return undefined;
  let url: URL;
  try {
    url = new URL(value.trim());
  } catch {
    return 'Enter a full link starting with https://';
  }
  if (url.protocol !== 'http:' && url.protocol !== 'https:') {
    return 'The image link must start with http:// or https://';
  }
  if (!IMAGE_EXTENSIONS.some((ext) => url.pathname.toLowerCase().endsWith(ext))) {
    return 'The link must point to a .png, .jpg, .jpeg or .webp image.';
  }
  return undefined;
}

function parseLocal(value: string): Date | null {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

export interface EventFormValues {
  title: string;
  location: string;
  start_time: string;
  end_time: string;
  capacity: string;
  organization_id: string;
  image_url: string;
  registration_deadline: string;
}

/**
 * ``isNew``: creating an event also requires a future start, a future deadline
 * and an organization. When editing, past dates of a running event stay valid.
 */
export function validateEventForm(
  values: EventFormValues,
  { isNew, now = new Date() }: { isNew: boolean; now?: Date },
): FieldErrors<keyof EventFormValues> {
  const errors: FieldErrors<keyof EventFormValues> = {};
  errors.title = requiredText(values.title, 'Title');
  errors.location = requiredText(values.location, 'Location');

  const start = parseLocal(values.start_time);
  const end = parseLocal(values.end_time);
  const deadline = parseLocal(values.registration_deadline);

  if (!start) errors.start_time = 'Choose when the event starts.';
  else if (isNew && start <= now) errors.start_time = 'The start time must be in the future.';

  if (!end) errors.end_time = 'Choose when the event ends.';
  else if (start && end <= start) errors.end_time = 'The end time must be after the start time.';

  if (deadline) {
    if (start && deadline > start) {
      errors.registration_deadline = 'Registrations must close before the event starts.';
    } else if (isNew && deadline <= now) {
      errors.registration_deadline = 'The registration deadline must be in the future.';
    }
  }

  const capacity = Number(values.capacity);
  if (!values.capacity.trim()) errors.capacity = 'Enter how many people can attend.';
  else if (!Number.isInteger(capacity) || capacity < 1) {
    errors.capacity = 'Capacity must be a whole number of at least 1.';
  } else if (capacity > 100000) errors.capacity = 'Capacity looks too large (max 100000).';

  if (isNew && !values.organization_id) errors.organization_id = 'Choose the organizing organization.';
  errors.image_url = imageUrlError(values.image_url);
  return withoutEmpty(errors);
}

export function withoutEmpty<K extends string>(errors: FieldErrors<K>): FieldErrors<K> {
  return Object.fromEntries(
    Object.entries(errors).filter(([, message]) => Boolean(message)),
  ) as FieldErrors<K>;
}
