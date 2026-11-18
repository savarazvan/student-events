import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router';

import Typography from '@mui/material/Typography';

import { listOrganizations } from '../../api/admin';
import { createEvent } from '../../api/events';
import LoadingBox from '../../components/common/LoadingBox';
import EventForm from '../../components/events/EventForm';
import type { EventFormData } from '../../components/events/EventForm';
import { useAuth } from '../../context/AuthContext';
import { ApiError } from '../../api/client';
import { useApiError } from '../../hooks/useApiError';
import { useFormValidation } from '../../hooks/useFormValidation';
import { validateEventForm } from '../../utils/validation';
import type { EventCategory, OrganizationResponse } from '../../types';

const emptyForm: EventFormData = {
  title: '',
  description: '',
  location: '',
  start_time: '',
  end_time: '',
  capacity: '',
  organization_id: '',
  image_url: '',
  category: 'OTHER',
  registration_deadline: '',
};

export default function EventCreateContainer() {
  const [form, setForm] = useState<EventFormData>(emptyForm);
  const [adminOrgs, setAdminOrgs] = useState<OrganizationResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const { user } = useAuth();
  const isSuperAdmin = user?.global_role === 'SUPER_ADMIN';
  const [orgsLoading, setOrgsLoading] = useState(isSuperAdmin);
  const { error, handleError, clearError } = useApiError();
  const navigate = useNavigate();
  const validation = useFormValidation<keyof EventFormData>(
    validateEventForm(form, { isNew: true }),
  );

  const userOrgs = useMemo<OrganizationResponse[]>(() => {
    if (isSuperAdmin) return [];
    return (user?.organization_memberships ?? [])
      .filter((m) => m.role === 'ORG_ADMIN' || m.role === 'ORGANIZER')
      .map((m) => ({
        id: m.organization_id,
        name: m.organization_name,
        description: null,
        contact_email: null,
      }));
  }, [user, isSuperAdmin]);

  const organizations = isSuperAdmin ? adminOrgs : userOrgs;

  useEffect(() => {
    if (!isSuperAdmin) return;
    let ignore = false;
    listOrganizations()
      .then((orgs) => {
        if (!ignore) {
          setAdminOrgs(orgs);
          setOrgsLoading(false);
        }
      })
      .catch((err) => {
        if (!ignore) {
          handleError(err);
          setOrgsLoading(false);
        }
      });
    return () => {
      ignore = true;
    };
  }, [isSuperAdmin, handleError]);

  const handleChange = (field: keyof EventFormData, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    validation.touch(field);
  };

  const toISO = (local: string) => (local ? new Date(local).toISOString() : '');

  const handleSubmit = async () => {
    clearError();
    if (!validation.attemptSubmit()) return;
    setLoading(true);
    try {
      const ev = await createEvent({
        title: form.title,
        description: form.description || null,
        location: form.location,
        start_time: toISO(form.start_time),
        end_time: toISO(form.end_time),
        capacity: Number(form.capacity),
        organization_id: form.organization_id,
        image_url: form.image_url || null,
        category: form.category as EventCategory,
        registration_deadline: form.registration_deadline
          ? toISO(form.registration_deadline)
          : null,
      });
      navigate(`/events/${ev.id}`);
    } catch (err) {
      if (err instanceof ApiError && err.status === 400 && /image/i.test(err.detail)) {
        validation.setServerErrors({ image_url: err.detail });
      } else if (!validation.applyServerErrors(err)) {
        handleError(err);
      }
    } finally {
      setLoading(false);
    }
  };

  if (orgsLoading) return <LoadingBox />;

  return (
    <>
      <Typography variant="h4" gutterBottom>
        Create Event
      </Typography>
      <EventForm
        data={form}
        organizations={organizations}
        error={error}
        fieldErrors={validation.errors}
        loading={loading}
        submitLabel="Create Event"
        onChange={handleChange}
        onSubmit={handleSubmit}
        onClearError={clearError}
      />
    </>
  );
}
