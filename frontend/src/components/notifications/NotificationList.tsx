import CampaignIcon from '@mui/icons-material/Campaign';
import CancelIcon from '@mui/icons-material/Cancel';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import EditCalendarIcon from '@mui/icons-material/EditCalendar';
import HourglassTopIcon from '@mui/icons-material/HourglassTop';
import NotificationsActiveIcon from '@mui/icons-material/NotificationsActive';
import StarIcon from '@mui/icons-material/Star';
import TaskAltIcon from '@mui/icons-material/TaskAlt';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import List from '@mui/material/List';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import type { ReactElement } from 'react';

import type { NotificationItem, NotificationType } from '../../types';
import { timeAgo } from '../../utils/time';

const ICONS: Record<NotificationType, ReactElement> = {
  REGISTRATION_CONFIRMED: <CheckCircleIcon color="success" />,
  REGISTRATION_WAITLISTED: <HourglassTopIcon color="warning" />,
  WAITLIST_PROMOTED: <TrendingUpIcon color="success" />,
  EVENT_UPDATED: <EditCalendarIcon color="info" />,
  EVENT_CANCELLED: <CancelIcon color="error" />,
  EVENT_ANNOUNCEMENT: <CampaignIcon color="primary" />,
  EVENT_REMINDER: <NotificationsActiveIcon color="primary" />,
  FEEDBACK_REQUESTED: <StarIcon color="warning" />,
  TASK_ASSIGNED: <TaskAltIcon color="secondary" />,
};

interface Props {
  items: NotificationItem[];
  dense?: boolean;
  onOpen: (notification: NotificationItem) => void;
}

export default function NotificationList({ items, dense, onOpen }: Props) {
  return (
    <List dense={dense} disablePadding>
      {items.map((n) => (
        <ListItemButton
          key={n.id}
          onClick={() => onOpen(n)}
          sx={{
            alignItems: 'flex-start',
            bgcolor: n.read_at ? 'transparent' : 'action.selected',
            borderRadius: 1,
            mb: 0.5,
          }}
        >
          <ListItemIcon sx={{ mt: 0.5, minWidth: 40 }}>{ICONS[n.type]}</ListItemIcon>
          <ListItemText
            primary={n.title}
            secondary={
              <>
                {n.message}
                <br />
                {timeAgo(n.created_at)}
              </>
            }
            slotProps={{
              primary: { fontWeight: n.read_at ? 'normal' : 'bold' },
              secondary: dense ? { sx: { whiteSpace: 'normal' } } : undefined,
            }}
          />
        </ListItemButton>
      ))}
    </List>
  );
}
