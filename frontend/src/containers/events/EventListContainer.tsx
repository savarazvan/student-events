import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router';

import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Pagination from '@mui/material/Pagination';
import Typography from '@mui/material/Typography';
import AddIcon from '@mui/icons-material/Add';

import { listEvents } from '../../api/events';
import ErrorAlert from '../../components/common/ErrorAlert';
import LoadingBox from '../../components/common/LoadingBox';
import EventFilters from '../../components/events/EventFilters';
import EventGrid from '../../components/events/EventGrid';
import { useAuth } from '../../context/AuthContext';
import { useApiError } from '../../hooks/useApiError';
import { useOrganizations } from '../../hooks/useOrganizations';
import type { EventCategory, EventResponse, EventStatus } from '../../types';

export default function EventListContainer() {
  const [events, setEvents] = useState<EventResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [status, setStatus] = useState('');
  const [organizationId, setOrganizationId] = useState('');
  const [startsAfter, setStartsAfter] = useState('');
  const [startsBefore, setStartsBefore] = useState('');
  const [loading, setLoading] = useState(true);
  const { error, handleError, clearError } = useApiError();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { organizations } = useOrganizations();

  const pageSize = 12;
  const canCreate =
    user?.global_role === 'SUPER_ADMIN' ||
    (user?.organization_memberships ?? []).some(
      (m) => m.role === 'ORG_ADMIN' || m.role === 'ORGANIZER',
    );

  useEffect(() => {
    let ignore = false;
    const toISO = (val: string) => {
      if (!val) return undefined;
      const d = new Date(val);
      return Number.isNaN(d.getTime()) ? undefined : d.toISOString();
    };

    listEvents({
      search: search || undefined,
      category: (category as EventCategory) || undefined,
      status: (status as EventStatus) || undefined,
      organization_id: organizationId || undefined,
      starts_after: toISO(startsAfter),
      starts_before: toISO(startsBefore),
      page,
      size: pageSize,
    })
      .then((res) => {
        if (!ignore) {
          setEvents(res.items);
          setTotal(res.total);
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
  }, [
    search,
    category,
    status,
    organizationId,
    startsAfter,
    startsBefore,
    page,
    handleError,
  ]);

  const handleSearchChange = (v: string) => {
    setSearch(v);
    setPage(1);
    setLoading(true);
  };

  const handleCategoryChange = (v: string) => {
    setCategory(v);
    setPage(1);
    setLoading(true);
  };

  const handleStatusChange = (v: string) => {
    setStatus(v);
    setPage(1);
    setLoading(true);
  };

  const handleOrganizationIdChange = (v: string) => {
    setOrganizationId(v);
    setPage(1);
    setLoading(true);
  };

  const handleStartsAfterChange = (v: string) => {
    setStartsAfter(v);
    setPage(1);
    setLoading(true);
  };

  const handleStartsBeforeChange = (v: string) => {
    setStartsBefore(v);
    setPage(1);
    setLoading(true);
  };

  const handleResetFilters = () => {
    setSearch('');
    setCategory('');
    setStatus('');
    setOrganizationId('');
    setStartsAfter('');
    setStartsBefore('');
    setPage(1);
    setLoading(true);
  };

  return (
    <>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h4">Events</Typography>
        {canCreate && (
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => navigate('/events/new')}
          >
            Create Event
          </Button>
        )}
      </Box>
      <EventFilters
        search={search}
        category={category}
        status={status}
        organizationId={organizationId}
        organizations={organizations}
        startsAfter={startsAfter}
        startsBefore={startsBefore}
        onSearchChange={handleSearchChange}
        onCategoryChange={handleCategoryChange}
        onStatusChange={handleStatusChange}
        onOrganizationIdChange={handleOrganizationIdChange}
        onStartsAfterChange={handleStartsAfterChange}
        onStartsBeforeChange={handleStartsBeforeChange}
        onReset={handleResetFilters}
      />
      <ErrorAlert message={error} onClose={clearError} />
      {loading ? (
        <LoadingBox />
      ) : (
        <>
          <EventGrid events={events} onEventClick={(id) => navigate(`/events/${id}`)} />
          {total > pageSize && (
            <Box display="flex" justifyContent="center" mt={3}>
              <Pagination
                count={Math.ceil(total / pageSize)}
                page={page}
                onChange={(_, p) => {
                  setPage(p);
                  setLoading(true);
                }}
                color="primary"
              />
            </Box>
          )}
        </>
      )}
    </>
  );
}
