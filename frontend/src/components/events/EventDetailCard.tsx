import CalendarTodayIcon from '@mui/icons-material/CalendarToday';
import CategoryIcon from '@mui/icons-material/Category';
import GroupsIcon from '@mui/icons-material/Groups';
import LocationOnIcon from '@mui/icons-material/LocationOn';
import PeopleIcon from '@mui/icons-material/People';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import CardMedia from '@mui/material/CardMedia';
import Chip from '@mui/material/Chip';
import Divider from '@mui/material/Divider';
import Typography from '@mui/material/Typography';
import type { ReactNode } from 'react';

import type { EventResponse } from '../../types';

function fmt(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: 'full',
    timeStyle: 'short',
  });
}

interface Props {
  event: EventResponse;
  organizationName?: string;
  actions?: ReactNode;
}

export default function EventDetailCard({ event, organizationName, actions }: Props) {
  return (
    <Card>
      {event.image_url && (
        <CardMedia component="img" height="280" image={event.image_url} alt={event.title} />
      )}
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
          <Typography variant="h4">{event.title}</Typography>
          <Chip label={event.status} color="primary" />
        </Box>

        {event.description && (
          <Typography variant="body1" color="text.secondary" paragraph>
            {event.description}
          </Typography>
        )}

        <Divider sx={{ my: 2 }} />

        <Box display="flex" flexWrap="wrap" gap={3}>
          {organizationName && (
            <Box display="flex" alignItems="center" gap={0.5}>
              <GroupsIcon color="action" />
              <Typography variant="body2">Organized by {organizationName}</Typography>
            </Box>
          )}
          <Box display="flex" alignItems="center" gap={0.5}>
            <CalendarTodayIcon color="action" />
            <Typography variant="body2">
              {fmt(event.start_time)} – {fmt(event.end_time)}
            </Typography>
          </Box>
          <Box display="flex" alignItems="center" gap={0.5}>
            <LocationOnIcon color="action" />
            <Typography variant="body2">{event.location}</Typography>
          </Box>
          <Box display="flex" alignItems="center" gap={0.5}>
            <PeopleIcon color="action" />
            <Typography variant="body2">Capacity: {event.capacity}</Typography>
          </Box>
          <Box display="flex" alignItems="center" gap={0.5}>
            <CategoryIcon color="action" />
            <Typography variant="body2">{event.category}</Typography>
          </Box>
        </Box>

        {event.registration_deadline && (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Registration deadline: {fmt(event.registration_deadline)}
          </Typography>
        )}

        {actions && (
          <Box sx={{ mt: 3, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            {actions}
          </Box>
        )}
      </CardContent>
    </Card>
  );
}
