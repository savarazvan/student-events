import { useState } from 'react';
import { useNavigate } from 'react-router';

import { login, register } from '../../api/auth';
import { ApiError } from '../../api/client';
import { useAuth } from '../../context/AuthContext';
import { useApiError } from '../../hooks/useApiError';
import { useFormValidation } from '../../hooks/useFormValidation';
import RegisterForm from '../../components/register/RegisterForm';
import type { RegisterField } from '../../components/register/RegisterForm';
import { emailError, passwordError, requiredText, withoutEmpty } from '../../utils/validation';

export default function RegisterContainer() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [loading, setLoading] = useState(false);
  const { error, handleError, clearError } = useApiError();
  const { signIn } = useAuth();
  const navigate = useNavigate();

  const { errors, touch, attemptSubmit, applyServerErrors, setServerErrors } =
    useFormValidation<RegisterField>(
      withoutEmpty({
        full_name: requiredText(fullName, 'Full name'),
        email: emailError(email),
        password: passwordError(password, true),
        confirm_password: !confirmPassword
          ? 'Repeat your password.'
          : confirmPassword !== password
            ? 'The two passwords do not match.'
            : undefined,
      }),
    );

  const handleSubmit = async () => {
    clearError();
    if (!attemptSubmit()) return;
    setLoading(true);
    try {
      await register({ email, password, full_name: fullName });
      // Auto-login after registration
      const res = await login({ email, password });
      await signIn(res.access_token);
      navigate('/');
    } catch (err) {
      if (err instanceof ApiError && err.status === 400 && /email/i.test(err.detail)) {
        setServerErrors({ email: 'An account with this e-mail already exists. Sign in instead.' });
      } else if (!applyServerErrors(err)) {
        handleError(err);
      }
    } finally {
      setLoading(false);
    }
  };

  const change = (field: RegisterField, setter: (v: string) => void) => (v: string) => {
    setter(v);
    touch(field);
  };

  return (
    <RegisterForm
      email={email}
      password={password}
      confirmPassword={confirmPassword}
      fullName={fullName}
      error={error}
      fieldErrors={errors}
      loading={loading}
      onEmailChange={change('email', setEmail)}
      onPasswordChange={change('password', setPassword)}
      onConfirmPasswordChange={change('confirm_password', setConfirmPassword)}
      onFullNameChange={change('full_name', setFullName)}
      onSubmit={handleSubmit}
      onClearError={clearError}
    />
  );
}
