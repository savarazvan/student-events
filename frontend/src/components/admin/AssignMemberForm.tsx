import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import MenuItem from '@mui/material/MenuItem';
import Select from '@mui/material/Select';
import type { SelectChangeEvent } from '@mui/material/Select';
import type { FormEvent } from 'react';

import type { AdminUserResponse, OrgRole, OrganizationResponse } from '../../types';
import UserSearchField from './UserSearchField';
import ErrorAlert from '../common/ErrorAlert';

interface Props {
  organizations: OrganizationResponse[];
  orgId: string;
  selectedUser: AdminUserResponse | null;
  role: OrgRole;
  error: string | null;
  loading: boolean;
  onOrgIdChange: (v: string) => void;
  onUserChange: (user: AdminUserResponse | null) => void;
  onRoleChange: (v: OrgRole) => void;
  onSubmit: () => void;
  onClearError: () => void;
}

export default function AssignMemberForm({
  organizations,
  orgId,
  selectedUser,
  role,
  error,
  loading,
  onOrgIdChange,
  onUserChange,
  onRoleChange,
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
      <FormControl fullWidth margin="normal" required>
        <InputLabel>Organization</InputLabel>
        <Select
          value={orgId}
          label="Organization"
          onChange={(e: SelectChangeEvent) => onOrgIdChange(e.target.value)}
        >
          {organizations.map((org) => (
            <MenuItem key={org.id} value={org.id}>
              {org.name}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
      <UserSearchField value={selectedUser} onChange={onUserChange} />
      <FormControl fullWidth margin="normal" required>
        <InputLabel>Organization Role</InputLabel>
        <Select
          value={role}
          label="Organization Role"
          onChange={(e: SelectChangeEvent) => onRoleChange(e.target.value as OrgRole)}
        >
          <MenuItem value="ORG_ADMIN">ORG_ADMIN (Administrator)</MenuItem>
          <MenuItem value="ORGANIZER">ORGANIZER</MenuItem>
          <MenuItem value="MEMBER">MEMBER</MenuItem>
        </Select>
      </FormControl>
      <Button
        type="submit"
        variant="contained"
        disabled={loading || !orgId || !selectedUser}
        sx={{ mt: 2 }}
      >
        {loading ? 'Assigning…' : 'Assign Member'}
      </Button>
    </Box>
  );
}
