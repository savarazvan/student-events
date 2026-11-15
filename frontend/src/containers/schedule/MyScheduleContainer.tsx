import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router';

import Box from '@mui/material/Box';
import FormControlLabel from '@mui/material/FormControlLabel';
import Switch from '@mui/material/Switch';
import Typography from '@mui/material/Typography';

import { getMyRegistrations } from '../../api/me';
import EmptyState from '../../components/common/EmptyState';
import ErrorAlert from '../../components/common/ErrorAlert';
import LoadingBox from '../../components/common/LoadingBox';
import RegistrationCard from '../../components/schedule/RegistrationCard';
import { useApiError } from '../../hooks/useApiError';
import type { MyRegistrationResponse } from '../../types';

export default function MyScheduleContainer() {
  const [registrations, setRegistrations] = useState<MyRegistrationResponse[]>([]);
  const [upcoming, setUpcoming] = useState(true);
  const [includeCancelled, setIncludeCancelled] = useState(false);
  const [loading, setLoading] = useState(true);
  const { error, handleError, clearError } = useApiError();
  const navigate = useNavigate();

  useEffect(() => {
    let ignore = false;
    getMyRegistrations(upcoming, includeCancelled)
      .then((regs) => {
        if (!ignore) {
          setRegistrations(regs);
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
  }, [upcoming, includeCancelled, handleError]);

  const handleUpcomingChange = (v: boolean) => {
    setUpcoming(v);
    setLoading(true);
  };

  const handleIncludeCancelledChange = (v: boolean) => {
    setIncludeCancelled(v);
    setLoading(true);
  };

  return (
    <>
      <Typography variant="h4" gutterBottom>
        My Schedule
      </Typography>
      <Box display="flex" gap={2} mb={2}>
        <FormControlLabel
          control={
            <Switch
              checked={upcoming}
              onChange={(_, v) => handleUpcomingChange(v)}
            />
          }
          label="Upcoming only"
        />
        <FormControlLabel
          control={
            <Switch
              checked={includeCancelled}
              onChange={(_, v) => handleIncludeCancelledChange(v)}
            />
          }
          label="Include cancelled"
        />
      </Box>
      <ErrorAlert message={error} onClose={clearError} />
      {loading ? (
        <LoadingBox />
      ) : registrations.length === 0 ? (
        <EmptyState message="No registrations yet. Browse events to sign up!" />
      ) : (
        registrations.map((reg) => (
          <RegistrationCard
            key={reg.id}
            reg={reg}
            onViewEvent={(id) => navigate(`/events/${id}`)}
            onViewTicket={(ticketId) => navigate(`/tickets/${ticketId}`)}
          />
        ))
      )}
    </>
  );
}
