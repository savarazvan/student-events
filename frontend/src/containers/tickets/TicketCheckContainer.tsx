import { useCallback, useEffect, useState } from 'react';
import { useLocation, useNavigate, useSearchParams } from 'react-router';

import CancelIcon from '@mui/icons-material/Cancel';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ConfirmationNumberIcon from '@mui/icons-material/ConfirmationNumber';
import HowToRegIcon from '@mui/icons-material/HowToReg';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Divider from '@mui/material/Divider';
import Typography from '@mui/material/Typography';

import { ApiError } from '../../api/client';
import { checkIn } from '../../api/events';
import { verifyTicket } from '../../api/tickets';
import ErrorAlert from '../../components/common/ErrorAlert';
import LoadingBox from '../../components/common/LoadingBox';
import { useAuth } from '../../context/AuthContext';
import type { TicketVerificationResponse } from '../../types';

const ORGANIZERS_ONLY = "Only the event's organizers can check tickets in.";

function fmt(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}

/**
 * Opened by a phone camera from the ticket QR code (``/ticket-check?token=...``).
 * Anyone sees whether the ticket is valid; the event's organizers can check the
 * attendee in with one tap.
 */
export default function TicketCheckContainer() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') ?? '';
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [ticket, setTicket] = useState<TicketVerificationResponse | null>(null);
  const [error, setError] = useState<string | null>(token ? null : 'This link does not contain a ticket.');
  const [checkingIn, setCheckingIn] = useState(false);
  const [checkedInMessage, setCheckedInMessage] = useState<string | null>(null);

  const load = useCallback(() => verifyTicket(token), [token]);

  useEffect(() => {
    if (!token || authLoading) return;
    let ignore = false;
    load()
      .then((res) => {
        if (!ignore) setTicket(res);
      })
      .catch((err) => {
        if (!ignore) {
          setError(err instanceof ApiError ? err.detail : 'Could not verify this ticket.');
        }
      });
    return () => {
      ignore = true;
    };
    // Re-verify after signing in: organizers then get the check-in button.
  }, [token, load, authLoading, user]);

  const handleCheckIn = async () => {
    if (!ticket) return;
    setCheckingIn(true);
    setError(null);
    try {
      const res = await checkIn(ticket.event.id, { token });
      setCheckedInMessage(`${res.full_name} is checked in. Welcome!`);
      setTicket(await load());
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Check-in failed. Try again.');
    } finally {
      setCheckingIn(false);
    }
  };

  if (!ticket && !error) return <LoadingBox />;

  const isHolderView =
    ticket?.check_in_unavailable_reason === ORGANIZERS_ONLY && ticket.attendee_name !== null;

  return (
    <Card sx={{ maxWidth: 480, mx: 'auto', mt: { xs: 1, sm: 4 } }}>
      <CardContent>
        <Box display="flex" alignItems="center" gap={1} mb={2}>
          <ConfirmationNumberIcon color="primary" />
          <Typography variant="h6">Ticket check</Typography>
        </Box>

        <ErrorAlert message={error} onClose={ticket ? () => setError(null) : undefined} />

        {ticket && (
          <>
            {ticket.state === 'VALID' && (
              <Alert icon={<CheckCircleIcon fontSize="large" />} severity="success" sx={{ mb: 2 }}>
                <Typography variant="h6">Valid ticket</Typography>
              </Alert>
            )}
            {ticket.state === 'USED' && (
              <Alert icon={<HowToRegIcon fontSize="large" />} severity="info" sx={{ mb: 2 }}>
                <Typography variant="h6">Already checked in</Typography>
                {ticket.checked_in_at && <>at {fmt(ticket.checked_in_at)}</>}
              </Alert>
            )}
            {ticket.state === 'REVOKED' && (
              <Alert icon={<CancelIcon fontSize="large" />} severity="error" sx={{ mb: 2 }}>
                <Typography variant="h6">Ticket cancelled</Typography>
                The registration was cancelled; this ticket is not valid.
              </Alert>
            )}

            {checkedInMessage && (
              <Alert severity="success" variant="filled" sx={{ mb: 2 }}>
                {checkedInMessage}
              </Alert>
            )}

            {ticket.attendee_name && (
              <Typography variant="h5" gutterBottom>
                {ticket.attendee_name}
              </Typography>
            )}
            <Typography variant="subtitle1" fontWeight="bold">
              {ticket.event.title}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {fmt(ticket.event.start_time)} – {fmt(ticket.event.end_time)}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {ticket.event.location}
            </Typography>

            <Divider sx={{ my: 2 }} />

            {ticket.can_check_in ? (
              <Button
                fullWidth
                size="large"
                variant="contained"
                color="success"
                disabled={checkingIn}
                onClick={handleCheckIn}
              >
                {checkingIn ? 'Checking in…' : 'Check in attendee'}
              </Button>
            ) : !user ? (
              <>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Organizers: sign in to check this ticket in.
                </Typography>
                <Button
                  fullWidth
                  variant="outlined"
                  onClick={() =>
                    navigate(
                      `/login?next=${encodeURIComponent(location.pathname + location.search)}`,
                    )
                  }
                >
                  Sign in as organizer
                </Button>
              </>
            ) : isHolderView ? (
              <Typography variant="body2" color="text.secondary">
                This is your ticket. Show the QR code at the entrance.
              </Typography>
            ) : (
              ticket.check_in_unavailable_reason &&
              !checkedInMessage && (
                <Alert severity="warning">{ticket.check_in_unavailable_reason}</Alert>
              )
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
