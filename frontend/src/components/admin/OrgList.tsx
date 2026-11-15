import Paper from '@mui/material/Paper';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';

import type { OrganizationResponse } from '../../types';
import EmptyState from '../common/EmptyState';

interface Props {
  organizations: OrganizationResponse[];
}

export default function OrgList({ organizations }: Props) {
  if (organizations.length === 0) {
    return <EmptyState message="No organizations yet." />;
  }
  return (
    <TableContainer component={Paper}>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Name</TableCell>
            <TableCell>Description</TableCell>
            <TableCell>Contact Email</TableCell>
            <TableCell>Organization ID (UUID)</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {organizations.map((org) => (
            <TableRow key={org.id}>
              <TableCell>{org.name}</TableCell>
              <TableCell>{org.description ?? '—'}</TableCell>
              <TableCell>{org.contact_email ?? '—'}</TableCell>
              <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>
                {org.id}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
