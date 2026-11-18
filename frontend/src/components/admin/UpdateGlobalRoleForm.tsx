import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import MenuItem from '@mui/material/MenuItem';
import Select from '@mui/material/Select';
import type { SelectChangeEvent } from '@mui/material/Select';
import type { FormEvent } from 'react';

import type { AdminUserResponse, GlobalRole } from '../../types';
import UserSearchField from './UserSearchField';
import ErrorAlert from '../common/ErrorAlert';

interface Props {
  selectedUser: AdminUserResponse | null;
  globalRole: GlobalRole;
  error: string | null;
  loading: boolean;
  onUserChange: (user: AdminUserResponse | null) => void;
  onGlobalRoleChange: (v: GlobalRole) => void;
  onSubmit: () => void;
  onClearError: () => void;
}

export default function UpdateGlobalRoleForm({
  selectedUser,
  globalRole,
  error,
  loading,
  onUserChange,
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
      <UserSearchField value={selectedUser} onChange={onUserChange} />
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
        disabled={loading || !selectedUser}
        sx={{ mt: 2 }}
      >
        {loading ? 'Updating…' : 'Update Global Role'}
      </Button>
    </Box>
  );
}
