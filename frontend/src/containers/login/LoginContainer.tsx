import { useState } from 'react';
import { useNavigate } from 'react-router';

import { login } from '../../api/auth';
import { useAuth } from '../../context/AuthContext';
import { useApiError } from '../../hooks/useApiError';
import LoginForm from '../../components/login/LoginForm';

export default function LoginContainer() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { error, handleError, clearError } = useApiError();
  const { signIn } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async () => {
    setLoading(true);
    clearError();
    try {
      const res = await login({ email, password });
      await signIn(res.access_token);
      navigate('/');
    } catch (err) {
      handleError(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <LoginForm
      email={email}
      password={password}
      error={error}
      loading={loading}
      onEmailChange={setEmail}
      onPasswordChange={setPassword}
      onSubmit={handleSubmit}
      onClearError={clearError}
    />
  );
}
