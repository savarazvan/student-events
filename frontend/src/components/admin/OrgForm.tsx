import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import type { FormEvent } from 'react';

import type { FieldErrors } from '../../utils/validation';
import ErrorAlert from '../common/ErrorAlert';

export type OrgField = 'name' | 'contact_email';

interface Props {
  name: string;
  description: string;
  contactEmail: string;
  error: string | null;
  fieldErrors: FieldErrors<OrgField>;
  loading: boolean;
  onNameChange: (v: string) => void;
  onDescriptionChange: (v: string) => void;
  onContactEmailChange: (v: string) => void;
  onSubmit: () => void;
  onClearError: () => void;
}

export default function OrgForm({
  name,
  description,
  contactEmail,
  error,
  fieldErrors,
  loading,
  onNameChange,
  onDescriptionChange,
  onContactEmailChange,
  onSubmit,
  onClearError,
}: Props) {
  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    onSubmit();
  };

  return (
    <Box component="form" onSubmit={handleSubmit} noValidate sx={{ maxWidth: 500 }}>
      <ErrorAlert message={error} onClose={onClearError} />
      <TextField
        margin="normal"
        required
        fullWidth
        label="Organization Name"
        value={name}
        error={Boolean(fieldErrors.name)}
        helperText={fieldErrors.name}
        onChange={(e) => onNameChange(e.target.value)}
      />
      <TextField
        margin="normal"
        fullWidth
        label="Description"
        multiline
        rows={2}
        value={description}
        onChange={(e) => onDescriptionChange(e.target.value)}
      />
      <TextField
        margin="normal"
        required
        fullWidth
        label="Contact Email"
        type="email"
        value={contactEmail}
        error={Boolean(fieldErrors.contact_email)}
        helperText={fieldErrors.contact_email}
        onChange={(e) => onContactEmailChange(e.target.value)}
      />
      <Button
        type="submit"
        variant="contained"
        disabled={loading}
        sx={{ mt: 2 }}
      >
        {loading ? 'Creating…' : 'Create Organization'}
      </Button>
    </Box>
  );
}
