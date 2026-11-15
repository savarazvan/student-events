import SearchIcon from '@mui/icons-material/Search';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import FormControl from '@mui/material/FormControl';
import InputAdornment from '@mui/material/InputAdornment';
import InputLabel from '@mui/material/InputLabel';
import MenuItem from '@mui/material/MenuItem';
import Select from '@mui/material/Select';
import TextField from '@mui/material/TextField';
import type { SelectChangeEvent } from '@mui/material/Select';

import type { EventCategory, EventStatus, OrganizationResponse } from '../../types';

const CATEGORIES: EventCategory[] = [
  'WORKSHOP',
  'CONFERENCE',
  'TRAINING',
  'SOCIAL',
  'VOLUNTEERING',
  'COMPETITION',
  'OTHER',
];

const STATUSES: EventStatus[] = [
  'DRAFT',
  'SUBMITTED',
  'PUBLISHED',
  'IN_PROGRESS',
  'COMPLETED',
  'CANCELLED',
];

interface Props {
  search: string;
  category: string;
  status: string;
  organizationId: string;
  organizations: OrganizationResponse[];
  startsAfter: string;
  startsBefore: string;
  onSearchChange: (v: string) => void;
  onCategoryChange: (v: string) => void;
  onStatusChange: (v: string) => void;
  onOrganizationIdChange: (v: string) => void;
  onStartsAfterChange: (v: string) => void;
  onStartsBeforeChange: (v: string) => void;
  onReset: () => void;
}

export default function EventFilters({
  search,
  category,
  status,
  organizationId,
  organizations,
  startsAfter,
  startsBefore,
  onSearchChange,
  onCategoryChange,
  onStatusChange,
  onOrganizationIdChange,
  onStartsAfterChange,
  onStartsBeforeChange,
  onReset,
}: Props) {
  const hasActiveFilters = Boolean(
    search || category || status || organizationId || startsAfter || startsBefore,
  );

  return (
    <Box display="flex" gap={2} mb={3} flexWrap="wrap" alignItems="center">
      <TextField
        size="small"
        placeholder="Search events…"
        value={search}
        onChange={(e) => onSearchChange(e.target.value)}
        slotProps={{
          input: {
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
          },
        }}
        sx={{ minWidth: 220 }}
      />
      <FormControl size="small" sx={{ minWidth: 150 }}>
        <InputLabel>Category</InputLabel>
        <Select
          value={category}
          label="Category"
          onChange={(e: SelectChangeEvent) => onCategoryChange(e.target.value)}
        >
          <MenuItem value="">All</MenuItem>
          {CATEGORIES.map((cat) => (
            <MenuItem key={cat} value={cat}>
              {cat.charAt(0) + cat.slice(1).toLowerCase()}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
      <FormControl size="small" sx={{ minWidth: 150 }}>
        <InputLabel>Status</InputLabel>
        <Select
          value={status}
          label="Status"
          onChange={(e: SelectChangeEvent) => onStatusChange(e.target.value)}
        >
          <MenuItem value="">Default</MenuItem>
          {STATUSES.map((st) => (
            <MenuItem key={st} value={st}>
              {st}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
      <FormControl size="small" sx={{ minWidth: 180 }}>
        <InputLabel>Organization</InputLabel>
        <Select
          value={organizationId}
          label="Organization"
          onChange={(e: SelectChangeEvent) => onOrganizationIdChange(e.target.value)}
        >
          <MenuItem value="">All</MenuItem>
          {organizations.map((org) => (
            <MenuItem key={org.id} value={org.id}>
              {org.name}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
      <TextField
        size="small"
        label="Starts After"
        type="datetime-local"
        value={startsAfter}
        onChange={(e) => onStartsAfterChange(e.target.value)}
        slotProps={{ inputLabel: { shrink: true } }}
      />
      <TextField
        size="small"
        label="Starts Before"
        type="datetime-local"
        value={startsBefore}
        onChange={(e) => onStartsBeforeChange(e.target.value)}
        slotProps={{ inputLabel: { shrink: true } }}
      />
      {hasActiveFilters && (
        <Button size="small" variant="text" onClick={onReset}>
          Reset Filters
        </Button>
      )}
    </Box>
  );
}
