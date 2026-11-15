import ConfirmationNumberIcon from '@mui/icons-material/ConfirmationNumber';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import Typography from '@mui/material/Typography';

import type { MyRegistrationResponse } from '../../types';

function fmt(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

interface Props {
  reg: MyRegistrationResponse;
  onViewTicket?: (ticketId: string) => void;
  onViewEvent?: (eventId: string) => void;
}

export default function RegistrationCard({ reg, onViewTicket, onViewEvent }: Props) {
  const statusColor =
    reg.status === 'CONFIRMED'
      ? 'success'
      : reg.status === 'WAITLIST'
        ? 'warning'
        : 'error';

  return (
    <Card sx={{ mb: 2 }}>
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
          <Typography variant="h6">{reg.event.title}</Typography>
          <Chip label={reg.status} color={statusColor} size="small" />
        </Box>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          {fmt(reg.event.start_time)} – {fmt(reg.event.end_time)}
        </Typography>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          {reg.event.location}
        </Typography>
        {reg.ticket_state && (
          <Chip
            label={`Ticket: ${reg.ticket_state}`}
            size="small"
            variant="outlined"
            sx={{ mr: 1, mt: 1 }}
          />
        )}
        {reg.checked_in_at && (
          <Chip
            label={`Checked in: ${fmt(reg.checked_in_at)}`}
            size="small"
            color="success"
            variant="outlined"
            sx={{ mt: 1 }}
          />
        )}
        <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
          {onViewEvent && (
            <Button size="small" onClick={() => onViewEvent(reg.event.id)}>
              View Event
            </Button>
          )}
          {reg.ticket_id && onViewTicket && (
            <Button
              size="small"
              startIcon={<ConfirmationNumberIcon />}
              onClick={() => onViewTicket(reg.ticket_id!)}
            >
              View Ticket
            </Button>
          )}
        </Box>
      </CardContent>
    </Card>
  );
}
