import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Paper from '@mui/material/Paper';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';

import type { AttendeeResponse } from '../../types';
import EmptyState from '../common/EmptyState';

interface Props {
  attendees: AttendeeResponse[];
  onCheckIn?: (userId: string) => void;
  onUndoCheckIn?: (ticketId: string) => void;
}

export default function AttendeeTable({
  attendees,
  onCheckIn,
  onUndoCheckIn,
}: Props) {
  if (attendees.length === 0) {
    return <EmptyState message="No attendees yet." />;
  }
  return (
    <TableContainer component={Paper}>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Name</TableCell>
            <TableCell>Email</TableCell>
            <TableCell>Status</TableCell>
            <TableCell>Registered At</TableCell>
            <TableCell>Checked In</TableCell>
            {(onCheckIn || onUndoCheckIn) && <TableCell align="right">Actions</TableCell>}
          </TableRow>
        </TableHead>
        <TableBody>
          {attendees.map((a) => (
            <TableRow key={a.user_id}>
              <TableCell>{a.full_name}</TableCell>
              <TableCell>{a.email}</TableCell>
              <TableCell>
                <Chip
                  label={a.status}
                  size="small"
                  color={a.status === 'CONFIRMED' ? 'success' : 'warning'}
                />
              </TableCell>
              <TableCell>
                {new Date(a.registered_at).toLocaleString()}
              </TableCell>
              <TableCell>
                {a.checked_in_at ? (
                  <Chip
                    icon={<CheckCircleIcon />}
                    label={new Date(a.checked_in_at).toLocaleString()}
                    size="small"
                    color="success"
                    variant="outlined"
                  />
                ) : (
                  '—'
                )}
              </TableCell>
              {(onCheckIn || onUndoCheckIn) && (
                <TableCell align="right">
                  {a.checked_in_at && a.ticket_id && onUndoCheckIn && (
                    <Button
                      size="small"
                      color="warning"
                      variant="outlined"
                      onClick={() => onUndoCheckIn(a.ticket_id!)}
                    >
                      Undo
                    </Button>
                  )}
                  {!a.checked_in_at && a.status === 'CONFIRMED' && onCheckIn && (
                    <Button
                      size="small"
                      color="primary"
                      variant="contained"
                      onClick={() => onCheckIn(a.user_id)}
                    >
                      Check In
                    </Button>
                  )}
                </TableCell>
              )}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
