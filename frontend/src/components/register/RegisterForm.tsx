import PersonAddIcon from '@mui/icons-material/PersonAdd';
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

export type RegisterField = 'full_name' | 'email' | 'password' | 'confirm_password';

interface Props {
  email: string;
  password: string;
  confirmPassword: string;
  fullName: string;
  error: string | null;
  fieldErrors: FieldErrors<RegisterField>;
  loading: boolean;
  onEmailChange: (v: string) => void;
  onPasswordChange: (v: string) => void;
  onConfirmPasswordChange: (v: string) => void;
  onFullNameChange: (v: string) => void;
  onSubmit: () => void;
  onClearError: () => void;
}

export default function RegisterForm({
  email,
  password,
  confirmPassword,
  fullName,
  error,
  fieldErrors,
  loading,
  onEmailChange,
  onPasswordChange,
  onConfirmPasswordChange,
  onFullNameChange,
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
      <Avatar sx={{ m: 1, bgcolor: 'secondary.main' }}>
        <PersonAddIcon />
      </Avatar>
      <Typography variant="h5" gutterBottom>
        Create Account
      </Typography>
      <ErrorAlert message={error} onClose={onClearError} />
      <Box component="form" onSubmit={handleSubmit} noValidate sx={{ width: '100%' }}>
        <TextField
          margin="normal"
          required
          fullWidth
          label="Full Name"
          autoComplete="name"
          autoFocus
          value={fullName}
          error={Boolean(fieldErrors.full_name)}
          helperText={fieldErrors.full_name}
          onChange={(e) => onFullNameChange(e.target.value)}
        />
        <TextField
          margin="normal"
          required
          fullWidth
          label="Email Address"
          type="email"
          autoComplete="email"
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
          autoComplete="new-password"
          value={password}
          error={Boolean(fieldErrors.password)}
          helperText={fieldErrors.password ?? 'At least 8 characters'}
          onChange={(e) => onPasswordChange(e.target.value)}
        />
        <TextField
          margin="normal"
          required
          fullWidth
          label="Confirm Password"
          type="password"
          autoComplete="new-password"
          value={confirmPassword}
          error={Boolean(fieldErrors.confirm_password)}
          helperText={fieldErrors.confirm_password}
          onChange={(e) => onConfirmPasswordChange(e.target.value)}
        />
        <Button
          type="submit"
          fullWidth
          variant="contained"
          disabled={loading}
          sx={{ mt: 2, mb: 2 }}
        >
          {loading ? 'Creating account…' : 'Register'}
        </Button>
        <Typography variant="body2" textAlign="center">
          Already have an account?{' '}
          <Link component={RouterLink} to="/login">
            Sign in
          </Link>
        </Typography>
      </Box>
    </Box>
  );
}
