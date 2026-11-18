import LockOutlinedIcon from '@mui/icons-material/LockOutlined';
import Avatar from '@mui/material/Avatar';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Link from '@mui/material/Link';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import type { FormEvent } from 'react';
import { Link as RouterLink } from 'react-router';

import type { FieldErrors } from '../../utils/validation';
import ErrorAlert from '../common/ErrorAlert';

export type LoginField = 'email' | 'password';

interface Props {
  email: string;
  password: string;
  error: string | null;
  fieldErrors: FieldErrors<LoginField>;
  loading: boolean;
  onEmailChange: (v: string) => void;
  onPasswordChange: (v: string) => void;
  onSubmit: () => void;
  onClearError: () => void;
}

export default function LoginForm({
  email,
  password,
  error,
  fieldErrors,
  loading,
  onEmailChange,
  onPasswordChange,
  onSubmit,
  onClearError,
}: Props) {
  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    onSubmit();
  };

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        maxWidth: 400,
        mx: 'auto',
        mt: 8,
      }}
    >
      <Avatar sx={{ m: 1, bgcolor: 'primary.main' }}>
        <LockOutlinedIcon />
      </Avatar>
      <Typography variant="h5" gutterBottom>
        Sign In
      </Typography>
      <ErrorAlert message={error} onClose={onClearError} />
      <Box component="form" onSubmit={handleSubmit} noValidate sx={{ width: '100%' }}>
        <TextField
          margin="normal"
          required
          fullWidth
          label="Email Address"
          type="email"
          autoComplete="email"
          autoFocus
          value={email}
          error={Boolean(fieldErrors.email)}
          helperText={fieldErrors.email}
          onChange={(e) => onEmailChange(e.target.value)}
        />
        <TextField
          margin="normal"
          required
          fullWidth
          label="Password"
          type="password"
          autoComplete="current-password"
          value={password}
          error={Boolean(fieldErrors.password)}
          helperText={fieldErrors.password}
          onChange={(e) => onPasswordChange(e.target.value)}
        />
        <Button
          type="submit"
          fullWidth
          variant="contained"
          disabled={loading}
          sx={{ mt: 2, mb: 2 }}
        >
          {loading ? 'Signing in…' : 'Sign In'}
        </Button>
        <Typography variant="body2" textAlign="center">
          No account yet?{' '}
          <Link component={RouterLink} to="/register">
            Create one
          </Link>
        </Typography>
      </Box>
    </Box>
  );
}
