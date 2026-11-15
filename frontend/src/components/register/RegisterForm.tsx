import PersonAddIcon from '@mui/icons-material/PersonAdd';
import Avatar from '@mui/material/Avatar';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import type { FormEvent } from 'react';

import ErrorAlert from '../common/ErrorAlert';

interface Props {
  email: string;
  password: string;
  fullName: string;
  error: string | null;
  loading: boolean;
  onEmailChange: (v: string) => void;
  onPasswordChange: (v: string) => void;
  onFullNameChange: (v: string) => void;
  onSubmit: () => void;
  onClearError: () => void;
}

export default function RegisterForm({
  email,
  password,
  fullName,
  error,
  loading,
  onEmailChange,
  onPasswordChange,
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
      <Box component="form" onSubmit={handleSubmit} sx={{ width: '100%' }}>
        <TextField
          margin="normal"
          required
          fullWidth
          label="Full Name"
          autoFocus
          value={fullName}
          onChange={(e) => onFullNameChange(e.target.value)}
        />
        <TextField
          margin="normal"
          required
          fullWidth
          label="Email Address"
          autoComplete="email"
          value={email}
          onChange={(e) => onEmailChange(e.target.value)}
        />
        <TextField
          margin="normal"
          required
          fullWidth
          label="Password"
          type="password"
          helperText="At least 8 characters"
          value={password}
          onChange={(e) => onPasswordChange(e.target.value)}
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
      </Box>
    </Box>
  );
}
