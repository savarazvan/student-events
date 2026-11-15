import { useState } from 'react';
import { useNavigate } from 'react-router';

import { login, register } from '../../api/auth';
import { useAuth } from '../../context/AuthContext';
import { useApiError } from '../../hooks/useApiError';
import RegisterForm from '../../components/register/RegisterForm';

export default function RegisterContainer() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [loading, setLoading] = useState(false);
  const { error, handleError, clearError } = useApiError();
  const { signIn } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async () => {
    setLoading(true);
    clearError();
    try {
      await register({ email, password, full_name: fullName });
      // Auto-login after registration
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
    <RegisterForm
      email={email}
      password={password}
      fullName={fullName}
      error={error}
      loading={loading}
      onEmailChange={setEmail}
      onPasswordChange={setPassword}
      onFullNameChange={setFullName}
      onSubmit={handleSubmit}
      onClearError={clearError}
    />
  );
}
