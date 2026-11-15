import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import MenuItem from '@mui/material/MenuItem';
import Select from '@mui/material/Select';
import TextField from '@mui/material/TextField';
import type { SelectChangeEvent } from '@mui/material/Select';
import type { FormEvent } from 'react';

import type { OrgRole, OrganizationResponse } from '../../types';
import ErrorAlert from '../common/ErrorAlert';

interface Props {
  organizations: OrganizationResponse[];
  orgId: string;
  userId: string;
  role: OrgRole;
  error: string | null;
  loading: boolean;
  onOrgIdChange: (v: string) => void;
  onUserIdChange: (v: string) => void;
  onRoleChange: (v: OrgRole) => void;
  onSubmit: () => void;
  onClearError: () => void;
}

export default function AssignMemberForm({
  organizations,
  orgId,
  userId,
  role,
  error,
  loading,
  onOrgIdChange,
  onUserIdChange,
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
        disabled={loading || !orgId || !userId}
        sx={{ mt: 2 }}
      >
        {loading ? 'Assigning…' : 'Assign Member'}
      </Button>
    </Box>
  );
}
