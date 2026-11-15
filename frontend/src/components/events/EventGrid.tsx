import Grid from '@mui/material/Grid';

import type { EventResponse } from '../../types';
import EmptyState from '../common/EmptyState';
import EventCard from './EventCard';

interface Props {
  events: EventResponse[];
  onEventClick: (id: string) => void;
}

export default function EventGrid({ events, onEventClick }: Props) {
  if (events.length === 0) {
    return <EmptyState message="No events found." />;
  }
  return (
    <Grid container spacing={3}>
      {events.map((event) => (
        <Grid key={event.id} size={{ xs: 12, sm: 6, md: 4 }}>
          <EventCard event={event} onClick={onEventClick} />
        </Grid>
      ))}
    </Grid>
  );
}
