import { useState } from 'react';
import NotificationsIcon from '@mui/icons-material/Notifications';
import Badge from '@mui/material/Badge';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Divider from '@mui/material/Divider';
import IconButton from '@mui/material/IconButton';
import Popover from '@mui/material/Popover';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import { useNavigate } from 'react-router';

import { useNotifications } from '../../context/NotificationsContext';
import type { NotificationItem } from '../../types';
import NotificationList from './NotificationList';

export default function NotificationBell() {
  const { items, unreadCount, markRead, markAllRead } = useNotifications();
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);
  const navigate = useNavigate();

  const handleOpen = async (n: NotificationItem) => {
    setAnchor(null);
    if (!n.read_at) await markRead(n.id).catch(() => {});
    if (n.event_id) navigate(`/events/${n.event_id}`);
  };

  return (
    <>
      <Tooltip title="Notifications">
        <IconButton color="inherit" onClick={(e) => setAnchor(e.currentTarget)}>
          <Badge badgeContent={unreadCount} color="error" max={99}>
            <NotificationsIcon />
          </Badge>
        </IconButton>
      </Tooltip>
      <Popover
        open={Boolean(anchor)}
        anchorEl={anchor}
        onClose={() => setAnchor(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        transformOrigin={{ vertical: 'top', horizontal: 'right' }}
        slotProps={{ paper: { sx: { width: 380, maxWidth: '95vw', maxHeight: 480 } } }}
      >
        <Box display="flex" justifyContent="space-between" alignItems="center" px={2} py={1}>
          <Typography variant="subtitle1" fontWeight="bold">
            Notifications
          </Typography>
          {unreadCount > 0 && (
            <Button size="small" onClick={() => markAllRead().catch(() => {})}>
              Mark all read
            </Button>
          )}
        </Box>
        <Divider />
        <Box px={1} py={1}>
          {items.length === 0 ? (
            <Typography variant="body2" color="text.secondary" sx={{ p: 2 }}>
              You have no notifications yet.
            </Typography>
          ) : (
            <NotificationList items={items.slice(0, 8)} dense onOpen={handleOpen} />
          )}
        </Box>
        <Divider />
        <Box textAlign="center" py={0.5}>
          <Button
            size="small"
            onClick={() => {
              setAnchor(null);
              navigate('/notifications');
            }}
          >
            See all
          </Button>
        </Box>
      </Popover>
    </>
  );
}
