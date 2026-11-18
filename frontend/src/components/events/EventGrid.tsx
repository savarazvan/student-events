import Grid from '@mui/material/Grid';

import { useOrganizations } from '../../hooks/useOrganizations';
import type { EventResponse } from '../../types';
import EmptyState from '../common/EmptyState';
import EventCard from './EventCard';

interface Props {
  events: EventResponse[];
  onEventClick: (id: string) => void;
}

export default function EventGrid({ events, onEventClick }: Props) {
  const { nameById } = useOrganizations();
  if (events.length === 0) {
    return <EmptyState message="No events found." />;
  }
  return (
    <Grid container spacing={3}>
      {events.map((event) => (
        <Grid key={event.id} size={{ xs: 12, sm: 6, md: 4 }}>
          <EventCard
            event={event}
            organizationName={nameById.get(event.organization_id)}
            onClick={onEventClick}
          />
        </Grid>
      ))}
    </Grid>
  );
}
