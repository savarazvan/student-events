import { useEffect, useState } from 'react';

import Autocomplete from '@mui/material/Autocomplete';
import TextField from '@mui/material/TextField';

import { searchUsers } from '../../api/admin';
import type { AdminUserResponse } from '../../types';

interface Props {
  value: AdminUserResponse | null;
  onChange: (user: AdminUserResponse | null) => void;
  label?: string;
}

/** Find an account by name or e-mail instead of typing its UUID. */
export default function UserSearchField({ value, onChange, label = 'User' }: Props) {
  const [input, setInput] = useState('');
  const [options, setOptions] = useState<AdminUserResponse[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let ignore = false;
    const timer = window.setTimeout(() => {
      setLoading(true);
      searchUsers(input)
        .then((res) => {
          if (!ignore) setOptions(res);
        })
        .catch(() => {})
        .finally(() => {
          if (!ignore) setLoading(false);
        });
    }, 250);
    return () => {
      ignore = true;
      window.clearTimeout(timer);
    };
  }, [input]);

  return (
    <Autocomplete
      value={value}
      onChange={(_, user) => onChange(user)}
      inputValue={input}
      onInputChange={(_, v) => setInput(v)}
      options={value && !options.some((o) => o.id === value.id) ? [value, ...options] : options}
      loading={loading}
      filterOptions={(x) => x}
      isOptionEqualToValue={(a, b) => a.id === b.id}
      getOptionLabel={(u) => `${u.full_name} (${u.email})`}
      renderInput={(params) => (
        <TextField {...params} label={label} placeholder="Search by name or e-mail" margin="normal" />
      )}
    />
  );
}
