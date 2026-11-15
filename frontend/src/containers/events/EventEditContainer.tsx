import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router';

import Typography from '@mui/material/Typography';

import { getEvent, updateEvent } from '../../api/events';
import LoadingBox from '../../components/common/LoadingBox';
import ErrorAlert from '../../components/common/ErrorAlert';
import EventForm from '../../components/events/EventForm';
import type { EventFormData } from '../../components/events/EventForm';
import { useApiError } from '../../hooks/useApiError';
import type { EventCategory } from '../../types';

function toLocal(iso: string | null): string {
  if (!iso) return '';
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export default function EventEditContainer() {
  const { eventId } = useParams<{ eventId: string }>();
  const navigate = useNavigate();
  const { error, handleError, clearError } = useApiError();

  const [form, setForm] = useState<EventFormData | null>(null);
  const [loading, setLoading] = useState(false);
  const [pageLoading, setPageLoading] = useState(true);

  useEffect(() => {
    if (!eventId) return;
    let ignore = false;

    getEvent(eventId)
      .then((ev) => {
        if (!ignore) {
          setForm({
            title: ev.title,
            description: ev.description ?? '',
            location: ev.location,
            start_time: toLocal(ev.start_time),
            end_time: toLocal(ev.end_time),
            capacity: String(ev.capacity),
            organization_id: ev.organization_id,
            image_url: ev.image_url ?? '',
            category: ev.category,
            registration_deadline: toLocal(ev.registration_deadline),
          });
          setPageLoading(false);
        }
      })
      .catch((err) => {
        if (!ignore) {
          handleError(err);
          setPageLoading(false);
        }
      });

    return () => {
      ignore = true;
    };
  }, [eventId, handleError]);

  const handleChange = (field: keyof EventFormData, value: string) => {
    setForm((prev) => (prev ? { ...prev, [field]: value } : prev));
  };

  const toISO = (local: string) => (local ? new Date(local).toISOString() : '');

  const handleSubmit = async () => {
    if (!eventId || !form) return;
    setLoading(true);
    clearError();
    try {
      await updateEvent(eventId, {
        title: form.title,
        description: form.description || null,
        location: form.location,
        start_time: toISO(form.start_time),
        end_time: toISO(form.end_time),
        capacity: Number(form.capacity),
        image_url: form.image_url || null,
        category: form.category as EventCategory,
        registration_deadline: form.registration_deadline
          ? toISO(form.registration_deadline)
          : null,
      });
      navigate(`/events/${eventId}`);
    } catch (err) {
      handleError(err);
    } finally {
      setLoading(false);
    }
  };

  if (pageLoading) return <LoadingBox />;
  if (!form) return <ErrorAlert message={error ?? 'Event not found.'} />;

  return (
    <>
      <Typography variant="h4" gutterBottom>
        Edit Event
      </Typography>
      <EventForm
        data={form}
        organizations={[]}
        error={error}
        loading={loading}
        submitLabel="Save Changes"
        onChange={handleChange}
        onSubmit={handleSubmit}
        onClearError={clearError}
        hideOrgField
      />
    </>
  );
}
