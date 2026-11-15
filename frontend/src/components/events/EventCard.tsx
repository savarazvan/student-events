import CalendarTodayIcon from '@mui/icons-material/CalendarToday';
import GroupsIcon from '@mui/icons-material/Groups';
import LocationOnIcon from '@mui/icons-material/LocationOn';
import PeopleIcon from '@mui/icons-material/People';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardActionArea from '@mui/material/CardActionArea';
import CardContent from '@mui/material/CardContent';
import CardMedia from '@mui/material/CardMedia';
import Chip from '@mui/material/Chip';
import Typography from '@mui/material/Typography';

import type { EventResponse } from '../../types';

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

const STATUS_COLOR: Record<string, 'success' | 'warning' | 'info' | 'error' | 'default'> = {
  PUBLISHED: 'success',
  IN_PROGRESS: 'info',
  DRAFT: 'default',
  SUBMITTED: 'warning',
  COMPLETED: 'default',
  CANCELLED: 'error',
};

interface Props {
  event: EventResponse;
  organizationName?: string;
  onClick: (id: string) => void;
}

export default function EventCard({ event, organizationName, onClick }: Props) {
  return (
    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <CardActionArea onClick={() => onClick(event.id)} sx={{ flex: 1 }}>
        {event.image_url && (
          <CardMedia
            component="img"
            height="160"
            image={event.image_url}
            alt={event.title}
          />
        )}
        <CardContent>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
            <Chip label={event.category} size="small" />
            <Chip
              label={event.status}
              size="small"
              color={STATUS_COLOR[event.status] ?? 'default'}
            />
          </Box>
          <Typography variant="h6" gutterBottom noWrap>
            {event.title}
          </Typography>
          {organizationName && (
            <Box display="flex" alignItems="center" gap={0.5} mb={0.5}>
              <GroupsIcon fontSize="small" color="action" />
              <Typography variant="body2" color="text.secondary" noWrap>
                {organizationName}
              </Typography>
            </Box>
          )}
          <Box display="flex" alignItems="center" gap={0.5} mb={0.5}>
            <CalendarTodayIcon fontSize="small" color="action" />
            <Typography variant="body2" color="text.secondary">
              {formatDate(event.start_time)}
            </Typography>
          </Box>
          <Box display="flex" alignItems="center" gap={0.5} mb={0.5}>
            <LocationOnIcon fontSize="small" color="action" />
            <Typography variant="body2" color="text.secondary" noWrap>
              {event.location}
            </Typography>
          </Box>
          <Box display="flex" alignItems="center" gap={0.5}>
            <PeopleIcon fontSize="small" color="action" />
            <Typography variant="body2" color="text.secondary">
              Capacity: {event.capacity}
            </Typography>
          </Box>
        </CardContent>
      </CardActionArea>
    </Card>
  );
}
