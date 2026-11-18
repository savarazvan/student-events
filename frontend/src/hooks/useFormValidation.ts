import { useCallback, useState } from 'react';

import { ApiError } from '../api/client';
import type { FieldErrors } from '../utils/validation';

/**
 * Field-level errors for a form.
 *
 * Client errors (from ``clientErrors``, recomputed every render) are shown for a
 * field once it has been edited or after the first submit attempt. Server
 * validation errors (422) are shown on their field until that field changes.
 */
export function useFormValidation<K extends string>(clientErrors: FieldErrors<K>) {
  const [touched, setTouched] = useState<Partial<Record<K, true>>>({});
  const [submitted, setSubmitted] = useState(false);
  const [serverErrors, setServerErrors] = useState<FieldErrors<K>>({});

  const errors: FieldErrors<K> = { ...serverErrors };
  for (const key of Object.keys(clientErrors) as K[]) {
    if (submitted || touched[key]) errors[key] = clientErrors[key];
  }

  const touch = useCallback((field: K) => {
    setTouched((prev) => (prev[field] ? prev : { ...prev, [field]: true }));
    setServerErrors((prev) => {
      if (!(field in prev)) return prev;
      const next = { ...prev };
      delete next[field];
      return next;
    });
  }, []);

  /** Marks the form as submitted; returns true when it may be sent. */
  const attemptSubmit = (): boolean => {
    setSubmitted(true);
    return Object.keys(clientErrors).length === 0;
  };

  /** Puts API field errors next to their fields; returns true if there were any. */
  const applyServerErrors = useCallback((err: unknown): boolean => {
    if (err instanceof ApiError && Object.keys(err.fields).length > 0) {
      setServerErrors(err.fields as FieldErrors<K>);
      return true;
    }
    return false;
  }, []);

  const reset = useCallback(() => {
    setTouched({});
    setSubmitted(false);
    setServerErrors({});
  }, []);

  return { errors, touch, attemptSubmit, applyServerErrors, setServerErrors, reset };
}
