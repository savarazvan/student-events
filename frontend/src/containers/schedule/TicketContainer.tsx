import { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router';

import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import Typography from '@mui/material/Typography';

import { getTicket, getTicketQrSvg } from '../../api/me';
import ErrorAlert from '../../components/common/ErrorAlert';
import LoadingBox from '../../components/common/LoadingBox';
import { useApiError } from '../../hooks/useApiError';
import type { TicketResponse } from '../../types';

function fmt(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

export default function TicketContainer() {
  const { ticketId } = useParams<{ ticketId: string }>();
  const { error, handleError, clearError } = useApiError();
  const [ticket, setTicket] = useState<TicketResponse | null>(null);
  const [qrUrl, setQrUrl] = useState<string | null>(null);
  const qrUrlRef = useRef<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!ticketId) return;
    let ignore = false;

    getTicket(ticketId)
      .then(async (t) => {
        if (!ignore) {
          setTicket(t);
          if (t.state !== 'REVOKED') {
            const blob = await getTicketQrSvg(ticketId);
            if (!ignore) {
              if (qrUrlRef.current) {
                URL.revokeObjectURL(qrUrlRef.current);
              }
              const url = URL.createObjectURL(blob);
              qrUrlRef.current = url;
              setQrUrl(url);
            }
          }
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!ignore) {
          handleError(err);
          setLoading(false);
        }
      });

    return () => {
      ignore = true;
    };
  }, [ticketId, handleError]);

  useEffect(() => {
    return () => {
      if (qrUrlRef.current) {
        URL.revokeObjectURL(qrUrlRef.current);
      }
    };
  }, []);

  if (loading) return <LoadingBox />;
  if (!ticket) return <ErrorAlert message={error ?? 'Ticket not found.'} />;

  const stateColor =
    ticket.state === 'VALID' ? 'success' : ticket.state === 'USED' ? 'info' : 'error';

  return (
    <Card sx={{ maxWidth: 500, mx: 'auto', mt: 4 }}>
      <CardContent>
        <Typography variant="h5" gutterBottom>
          {ticket.event.title}
        </Typography>
        <Chip label={ticket.state} color={stateColor} sx={{ mb: 2 }} />
        <Typography variant="body2" color="text.secondary">
          {fmt(ticket.event.start_time)} – {fmt(ticket.event.end_time)}
        </Typography>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          {ticket.event.location}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Issued: {fmt(ticket.issued_at)}
        </Typography>
        {ticket.checked_in_at && (
          <Typography variant="body2" color="text.secondary">
            Checked in: {fmt(ticket.checked_in_at)}
          </Typography>
        )}
        <ErrorAlert message={error} onClose={clearError} />
        {qrUrl && (
          <Box display="flex" justifyContent="center" mt={3}>
            <img src={qrUrl} alt="QR Ticket" width={250} height={250} />
          </Box>
        )}
        {ticket.qr_token && (
          <Box mt={2} textAlign="center">
            <Typography variant="caption" color="text.secondary" display="block">
              QR Token:
            </Typography>
            <Typography
              variant="body2"
              sx={{
                fontFamily: 'monospace',
                wordBreak: 'break-all',
                bgcolor: 'action.hover',
                p: 1,
                borderRadius: 1,
                mt: 0.5,
              }}
            >
              {ticket.qr_token}
            </Typography>
          </Box>
        )}
        {ticket.state === 'REVOKED' && (
          <Typography variant="body1" color="error" textAlign="center" mt={2}>
            This ticket has been revoked.
          </Typography>
        )}
      </CardContent>
    </Card>
  );
}
