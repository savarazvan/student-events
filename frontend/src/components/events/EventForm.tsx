import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import MenuItem from '@mui/material/MenuItem';
import Select from '@mui/material/Select';
import TextField from '@mui/material/TextField';
import type { SelectChangeEvent } from '@mui/material/Select';
import type { FormEvent } from 'react';

import type { EventCategory, OrganizationResponse } from '../../types';
import ErrorAlert from '../common/ErrorAlert';

const CATEGORIES: EventCategory[] = [
  'WORKSHOP', 'CONFERENCE', 'TRAINING', 'SOCIAL',
  'VOLUNTEERING', 'COMPETITION', 'OTHER',
];

export interface EventFormData {
  title: string;
  description: string;
  location: string;
  start_time: string;
  end_time: string;
  capacity: string;
  organization_id: string;
  image_url: string;
  category: EventCategory;
  registration_deadline: string;
}

interface Props {
  data: EventFormData;
  organizations: OrganizationResponse[];
  error: string | null;
  loading: boolean;
  submitLabel: string;
  onChange: (field: keyof EventFormData, value: string) => void;
  onSubmit: () => void;
  onClearError: () => void;
  hideOrgField?: boolean;
}

export default function EventForm({
  data,
  organizations,
  error,
  loading,
  submitLabel,
  onChange,
  onSubmit,
  onClearError,
  hideOrgField,
}: Props) {
  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    onSubmit();
  };

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ maxWidth: 600 }}>
      <ErrorAlert message={error} onClose={onClearError} />
      <TextField
        margin="normal"
        required
        fullWidth
        label="Title"
        value={data.title}
        onChange={(e) => onChange('title', e.target.value)}
      />
      <TextField
        margin="normal"
        fullWidth
        label="Description"
        multiline
        rows={3}
        value={data.description}
        onChange={(e) => onChange('description', e.target.value)}
      />
      <TextField
        margin="normal"
        required
        fullWidth
        label="Location"
        value={data.location}
        onChange={(e) => onChange('location', e.target.value)}
      />
      <Box display="flex" gap={2}>
        <TextField
          margin="normal"
          required
          fullWidth
          label="Start Time"
          type="datetime-local"
          value={data.start_time}
          onChange={(e) => onChange('start_time', e.target.value)}
          slotProps={{ inputLabel: { shrink: true } }}
        />
        <TextField
          margin="normal"
          required
          fullWidth
          label="End Time"
          type="datetime-local"
          value={data.end_time}
          onChange={(e) => onChange('end_time', e.target.value)}
          slotProps={{ inputLabel: { shrink: true } }}
        />
      </Box>
      <Box display="flex" gap={2}>
        <TextField
          margin="normal"
          required
          fullWidth
          label="Capacity"
          type="number"
          value={data.capacity}
          onChange={(e) => onChange('capacity', e.target.value)}
          slotProps={{ htmlInput: { min: 1 } }}
        />
        <TextField
          margin="normal"
          fullWidth
          label="Registration Deadline"
          type="datetime-local"
          value={data.registration_deadline}
          onChange={(e) => onChange('registration_deadline', e.target.value)}
          slotProps={{ inputLabel: { shrink: true } }}
        />
      </Box>
      {!hideOrgField && (
        <FormControl fullWidth margin="normal" required>
          <InputLabel>Organization</InputLabel>
          <Select
            value={data.organization_id}
            label="Organization"
            onChange={(e: SelectChangeEvent) => onChange('organization_id', e.target.value)}
          >
            {organizations.map((org) => (
              <MenuItem key={org.id} value={org.id}>
                {org.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      )}
      <FormControl fullWidth margin="normal">
        <InputLabel>Category</InputLabel>
        <Select
          value={data.category}
          label="Category"
          onChange={(e: SelectChangeEvent) => onChange('category', e.target.value)}
        >
          {CATEGORIES.map((cat) => (
            <MenuItem key={cat} value={cat}>
              {cat.charAt(0) + cat.slice(1).toLowerCase()}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
      <TextField
        margin="normal"
        fullWidth
        label="Image URL"
        placeholder="https://example.com/image.jpg"
        value={data.image_url}
        onChange={(e) => onChange('image_url', e.target.value)}
      />
      <Button
        type="submit"
        variant="contained"
        disabled={loading}
        sx={{ mt: 2 }}
      >
        {loading ? 'Saving…' : submitLabel}
      </Button>
    </Box>
  );
}
