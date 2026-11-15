import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router';

import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Tab from '@mui/material/Tab';
import Tabs from '@mui/material/Tabs';
import Typography from '@mui/material/Typography';

import {
  cancelRegistration,
  checkIn,
  getAttendanceStats,
  getAttendees,
  getEvent,
  getMyRegistration,
  manualCheckIn,
  registerForEvent,
  undoCheckIn,
  updateEventStatus,
} from '../../api/events';
import AppSnackbar from '../../components/common/AppSnackbar';
import ErrorAlert from '../../components/common/ErrorAlert';
import LoadingBox from '../../components/common/LoadingBox';
import AttendanceStats from '../../components/events/AttendanceStats';
import AttendeeTable from '../../components/events/AttendeeTable';
import EventDetailCard from '../../components/events/EventDetailCard';
import QrCameraScanner from '../../components/events/QrCameraScanner';
import type { ScanOutcome } from '../../components/events/QrCameraScanner';
import QrCheckInForm from '../../components/events/QrCheckInForm';
import { useAuth } from '../../context/AuthContext';
import { ApiError } from '../../api/client';
import { useApiError } from '../../hooks/useApiError';
import { useOrganizations } from '../../hooks/useOrganizations';
import { useSnackbar } from '../../hooks/useSnackbar';
import type {
  AttendanceStatsResponse,
  AttendeeResponse,
  EventRegistrationResponse,
  EventResponse,
  EventStatus,
} from '../../types';
import EventAnnouncementsContainer from './EventAnnouncementsContainer';
import EventFeedbackContainer from './EventFeedbackContainer';
import EventReportContainer from './EventReportContainer';
import EventTeamContainer from './EventTeamContainer';

type DetailTab = 'details' | 'manage' | 'team' | 'report';

export default function EventDetailContainer() {
  const { eventId } = useParams<{ eventId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { error, handleError, clearError } = useApiError();
  const { snackbar, showSnackbar, closeSnackbar } = useSnackbar();

  const [event, setEvent] = useState<EventResponse | null>(null);
  const [myReg, setMyReg] = useState<EventRegistrationResponse | null>(null);
  const [attendees, setAttendees] = useState<AttendeeResponse[]>([]);
  const [stats, setStats] = useState<AttendanceStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [qrToken, setQrToken] = useState('');
  const [qrLoading, setQrLoading] = useState(false);
  const [tab, setTab] = useState<DetailTab>('details');
  const [scannerOpen, setScannerOpen] = useState(false);
  const { nameById } = useOrganizations();

  const isSuperAdmin = user?.global_role === 'SUPER_ADMIN';
  const isOrgAdmin = Boolean(
    event &&
      user?.organization_memberships.some(
        (m) => m.organization_id === event.organization_id && m.role === 'ORG_ADMIN',
      ),
  );
  const isOrgManager =
    event &&
    user?.organization_memberships.some(
      (m) =>
        m.organization_id === event.organization_id &&
        (m.role === 'ORG_ADMIN' || m.role === 'ORGANIZER'),
    );
  const canManage = Boolean(isSuperAdmin || isOrgManager);
  const isTeamMember = Boolean(
    isSuperAdmin ||
      (event &&
        user?.organization_memberships.some((m) => m.organization_id === event.organization_id)),
  );
  const canApproveOrAdvance = Boolean(isSuperAdmin || isOrgAdmin);

  useEffect(() => {
    if (!eventId) return;
    let ignore = false;

    getEvent(eventId)
      .then((ev) => {
        if (!ignore) {
          setEvent(ev);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!ignore) {
          handleError(err);
          setLoading(false);
        }
      });

    if (user) {
      getMyRegistration(eventId)
        .then((reg) => {
          if (!ignore) {
            setMyReg(reg);
          }
        })
        .catch(() => {
          if (!ignore) {
            setMyReg(null);
          }
        });
    }

    return () => {
      ignore = true;
    };
  }, [eventId, user, handleError]);

  // Fetch attendees / stats when the manage tab is shown
  useEffect(() => {
    if (!canManage || !eventId || tab !== 'manage') return;
    let ignore = false;

    Promise.all([getAttendees(eventId), getAttendanceStats(eventId)])
      .then(([att, st]) => {
        if (!ignore) {
          setAttendees(att);
          setStats(st);
        }
      })
      .catch((err) => {
        if (!ignore) {
          handleError(err);
        }
      });

    return () => {
      ignore = true;
    };
  }, [canManage, eventId, tab, handleError]);

  const handleRegister = async () => {
    if (!eventId) return;
    setActionLoading(true);
    try {
      const reg = await registerForEvent(eventId);
      setMyReg(reg);
      showSnackbar(
        reg.status === 'CONFIRMED'
          ? 'Registered! Check your ticket.'
          : 'Added to the waitlist.',
      );
    } catch (err) {
      handleError(err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancelReg = async () => {
    if (!eventId) return;
    setActionLoading(true);
    try {
      await cancelRegistration(eventId);
      setMyReg(null);
      showSnackbar('Registration cancelled.', 'info');
    } catch (err) {
      handleError(err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleStatusChange = async (status: EventStatus) => {
    if (!eventId) return;
    setActionLoading(true);
    try {
      const updated = await updateEventStatus(eventId, { status });
      setEvent(updated);
      showSnackbar(`Event status changed to ${status}.`);
    } catch (err) {
      handleError(err);
    } finally {
      setActionLoading(false);
    }
  };

  const refreshAttendance = async () => {
    if (!eventId) return;
    const [att, st] = await Promise.all([getAttendees(eventId), getAttendanceStats(eventId)]);
    setAttendees(att);
    setStats(st);
  };

  const checkInToken = async (token: string): Promise<ScanOutcome> => {
    if (!eventId) return { ok: false, message: 'Unknown event.' };
    try {
      const res = await checkIn(eventId, { token });
      await refreshAttendance();
      return { ok: true, message: `Welcome, ${res.full_name}! (${res.email})` };
    } catch (err) {
      return {
        ok: false,
        message: err instanceof ApiError ? err.detail : 'Check-in failed. Try again.',
      };
    }
  };

  const handleQrCheckIn = async () => {
    if (!qrToken.trim()) return;
    setQrLoading(true);
    clearError();
    const outcome = await checkInToken(qrToken.trim());
    if (outcome.ok) {
      showSnackbar(outcome.message);
      setQrToken('');
    } else {
      handleError(new Error(outcome.message));
    }
    setQrLoading(false);
  };

  const handleCheckInAttendee = async (userId: string) => {
    if (!eventId) return;
    try {
      await manualCheckIn(eventId, { user_id: userId });
      showSnackbar('Attendee checked in successfully.');
      await refreshAttendance();
    } catch (err) {
      handleError(err);
    }
  };

  const handleUndoCheckInAttendee = async (ticketId: string) => {
    if (!eventId) return;
    try {
      await undoCheckIn(eventId, ticketId);
      showSnackbar('Check-in undone.', 'info');
      await refreshAttendance();
    } catch (err) {
      handleError(err);
    }
  };

  if (loading) return <LoadingBox />;
  if (!event) return <ErrorAlert message={error ?? 'Event not found.'} />;

  const canRegister =
    user &&
    event.status === 'PUBLISHED' &&
    (!myReg || myReg.status === 'CANCELLED');

  const canCancelReg =
    myReg && (myReg.status === 'CONFIRMED' || myReg.status === 'WAITLIST');

  const canEditEvent =
    canManage && event.status !== 'COMPLETED' && event.status !== 'CANCELLED';

  const canCheckIn =
    event.status === 'PUBLISHED' || event.status === 'IN_PROGRESS';

  // Status transitions (ORGANIZER can only Submit / Back to Draft; ORG_ADMIN and SUPER_ADMIN can perform all allowed transitions)
  const statusActions: { label: string; target: EventStatus }[] = [];
  if (canManage) {
    const s = event.status;
    if (s === 'DRAFT') {
      statusActions.push({ label: 'Submit', target: 'SUBMITTED' });
      if (canApproveOrAdvance) {
        statusActions.push({ label: 'Publish', target: 'PUBLISHED' });
        statusActions.push({ label: 'Cancel', target: 'CANCELLED' });
      }
    }
    if (s === 'SUBMITTED') {
      statusActions.push({ label: 'Back to Draft', target: 'DRAFT' });
      if (canApproveOrAdvance) {
        statusActions.push({ label: 'Publish', target: 'PUBLISHED' });
        statusActions.push({ label: 'Cancel', target: 'CANCELLED' });
      }
    }
    if (s === 'PUBLISHED' && canApproveOrAdvance) {
      statusActions.push({ label: 'Start', target: 'IN_PROGRESS' });
      statusActions.push({ label: 'Cancel', target: 'CANCELLED' });
    }
    if (s === 'IN_PROGRESS' && canApproveOrAdvance) {
      statusActions.push({ label: 'Complete', target: 'COMPLETED' });
      statusActions.push({ label: 'Cancel', target: 'CANCELLED' });
    }
  }

  return (
    <>
      <ErrorAlert message={error} onClose={clearError} />

      {(canManage || isTeamMember) && (
        <Tabs value={tab} onChange={(_, v: DetailTab) => setTab(v)} sx={{ mb: 2 }}>
          <Tab label="Details" value="details" />
          {canManage && <Tab label="Check-in" value="manage" />}
          {isTeamMember && <Tab label="Team" value="team" />}
          {canManage && <Tab label="Report" value="report" />}
        </Tabs>
      )}

      {tab === 'details' && (
        <>
        <EventDetailCard
          event={event}
          organizationName={nameById.get(event.organization_id)}
          actions={
            <>
              {canRegister && (
                <Button
                  variant="contained"
                  disabled={actionLoading}
                  onClick={handleRegister}
                >
                  Register
                </Button>
              )}
              {canCancelReg && (
                <Button
                  variant="outlined"
                  color="error"
                  disabled={actionLoading}
                  onClick={handleCancelReg}
                >
                  Cancel Registration
                </Button>
              )}
              {myReg && myReg.status !== 'CANCELLED' && (
                <Typography variant="body2" sx={{ alignSelf: 'center' }}>
                  Status: {myReg.status}
                  {myReg.ticket_id && ' • Ticket issued'}
                </Typography>
              )}
              {myReg && myReg.status !== 'CANCELLED' && myReg.ticket_id && (
                <Button
                  variant="outlined"
                  onClick={() => navigate(`/tickets/${myReg.ticket_id}`)}
                >
                  View My Ticket
                </Button>
              )}
              {canEditEvent && (
                <Button
                  variant="outlined"
                  onClick={() => navigate(`/events/${event.id}/edit`)}
                >
                  Edit Event
                </Button>
              )}
              {statusActions.map((a) => (
                <Button
                  key={a.target}
                  variant="outlined"
                  color={a.target === 'CANCELLED' ? 'error' : 'primary'}
                  disabled={actionLoading}
                  onClick={() => handleStatusChange(a.target)}
                >
                  {a.label}
                </Button>
              ))}
            </>
          }
        />
        <EventAnnouncementsContainer
          eventId={event.id}
          canPost={canManage && !['DRAFT', 'SUBMITTED'].includes(event.status)}
          onPosted={(n) => showSnackbar(`Announcement sent to ${n} participant(s).`)}
        />
        {event.status === 'COMPLETED' && myReg?.checked_in_at && (
          <EventFeedbackContainer
            eventId={event.id}
            onSaved={() => showSnackbar('Thanks for your feedback!')}
          />
        )}
        </>
      )}

      {tab === 'manage' && canManage && (
        <Box>
          {stats && <AttendanceStats stats={stats} />}
          <QrCheckInForm
            token={qrToken}
            loading={qrLoading}
            disabled={!canCheckIn}
            onTokenChange={setQrToken}
            onSubmit={handleQrCheckIn}
            onOpenCamera={() => setScannerOpen(true)}
          />
          <QrCameraScanner
            open={scannerOpen}
            onClose={() => setScannerOpen(false)}
            onScan={checkInToken}
          />
          <Typography variant="h6" sx={{ mb: 1, mt: 2 }}>
            Attendees
          </Typography>
          <AttendeeTable
            attendees={attendees}
            onCheckIn={canCheckIn ? handleCheckInAttendee : undefined}
            onUndoCheckIn={canCheckIn ? handleUndoCheckInAttendee : undefined}
          />
        </Box>
      )}

      {tab === 'team' && isTeamMember && user && (
        <EventTeamContainer event={event} currentUserId={user.id} canPlan={canManage} />
      )}

      {tab === 'report' && canManage && <EventReportContainer eventId={event.id} />}

      <AppSnackbar
        open={snackbar.open}
        message={snackbar.message}
        severity={snackbar.severity}
        onClose={closeSnackbar}
      />
    </>
  );
}
