import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import MenuItem from '@mui/material/MenuItem';
import Select from '@mui/material/Select';
import TextField from '@mui/material/TextField';
import type { SelectChangeEvent } from '@mui/material/Select';
import type { FormEvent } from 'react';

import type { GlobalRole } from '../../types';
import ErrorAlert from '../common/ErrorAlert';

interface Props {
  userId: string;
  globalRole: GlobalRole;
  error: string | null;
  loading: boolean;
  onUserIdChange: (v: string) => void;
  onGlobalRoleChange: (v: GlobalRole) => void;
  onSubmit: () => void;
  onClearError: () => void;
}

export default function UpdateGlobalRoleForm({
  userId,
  globalRole,
  error,
  loading,
  onUserIdChange,
  onGlobalRoleChange,
  onSubmit,
  onClearError,
}: Props) {
  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    onSubmit();
  };

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ maxWidth: 500 }}>
      <ErrorAlert message={error} onClose={onClearError} />
      <TextField
        margin="normal"
        required
        fullWidth
        label="User ID (UUID)"
        placeholder="e.g. 8e4ba76e-55c8-4f5b-86a6-0669d128a442"
        value={userId}
        onChange={(e) => onUserIdChange(e.target.value)}
      />
      <FormControl fullWidth margin="normal" required>
        <InputLabel>Global Role</InputLabel>
        <Select
          value={globalRole}
          label="Global Role"
          onChange={(e: SelectChangeEvent) =>
            onGlobalRoleChange(e.target.value as GlobalRole)
          }
        >
          <MenuItem value="USER">USER (Standard Student/Organizer)</MenuItem>
          <MenuItem value="SUPER_ADMIN">SUPER_ADMIN (Platform Administrator)</MenuItem>
        </Select>
      </FormControl>
      <Button
        type="submit"
        variant="contained"
        disabled={loading || !userId}
        sx={{ mt: 2 }}
      >
        {loading ? 'Updating…' : 'Update Global Role'}
      </Button>
    </Box>
  );
}
