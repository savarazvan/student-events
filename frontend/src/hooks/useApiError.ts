import { useCallback, useState } from 'react';

import { ApiError } from '../api/client';

export function useApiError() {
  const [error, setError] = useState<string | null>(null);

  const handleError = useCallback((err: unknown) => {
    if (err instanceof ApiError) {
      setError(err.detail);
    } else if (err instanceof Error) {
      setError(err.message);
    } else {
      setError('An unexpected error occurred.');
    }
  }, []);

  const clearError = useCallback(() => setError(null), []);

  return { error, handleError, clearError };
}
