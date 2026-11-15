import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router';

import { login } from '../../api/auth';
import { ApiError } from '../../api/client';
import { useAuth } from '../../context/AuthContext';
import { useApiError } from '../../hooks/useApiError';
import { useFormValidation } from '../../hooks/useFormValidation';
import LoginForm from '../../components/login/LoginForm';
import type { LoginField } from '../../components/login/LoginForm';
import { emailError, passwordError, withoutEmpty } from '../../utils/validation';

/** Only follow redirects inside the app (avoids open redirects via ?next=). */
function safeNext(next: string | null): string {
  return next && next.startsWith('/') && !next.startsWith('//') ? next : '/';
}

export default function LoginContainer() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { error, handleError, clearError } = useApiError();
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const { errors, touch, attemptSubmit, applyServerErrors } = useFormValidation<LoginField>(
    withoutEmpty({ email: emailError(email), password: passwordError(password, false) }),
  );

  const handleSubmit = async () => {
    clearError();
    if (!attemptSubmit()) return;
    setLoading(true);
    try {
      const res = await login({ email, password });
      await signIn(res.access_token);
      navigate(safeNext(searchParams.get('next')));
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        handleError(new Error('Incorrect e-mail or password. Check them and try again.'));
      } else if (!applyServerErrors(err)) {
        handleError(err);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <LoginForm
      email={email}
      password={password}
      error={error}
      fieldErrors={errors}
      loading={loading}
      onEmailChange={(v) => {
        setEmail(v);
        touch('email');
      }}
      onPasswordChange={(v) => {
        setPassword(v);
        touch('password');
      }}
      onSubmit={handleSubmit}
      onClearError={clearError}
    />
  );
}
