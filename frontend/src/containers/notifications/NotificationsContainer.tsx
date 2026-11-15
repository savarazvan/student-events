import { useEffect } from 'react';
import { useNavigate } from 'react-router';

import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Typography from '@mui/material/Typography';

import EmptyState from '../../components/common/EmptyState';
import NotificationList from '../../components/notifications/NotificationList';
import { useNotifications } from '../../context/NotificationsContext';
import type { NotificationItem } from '../../types';

export default function NotificationsContainer() {
  const { items, unreadCount, refresh, markRead, markAllRead } = useNotifications();
  const navigate = useNavigate();

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const handleOpen = async (n: NotificationItem) => {
    if (!n.read_at) await markRead(n.id).catch(() => {});
    if (n.event_id) navigate(`/events/${n.event_id}`);
  };

  return (
    <>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h4">Notifications</Typography>
        {unreadCount > 0 && (
          <Button variant="outlined" onClick={() => markAllRead().catch(() => {})}>
            Mark all as read ({unreadCount})
          </Button>
        )}
      </Box>
      <Typography variant="body2" color="text.secondary" mb={2}>
        Registration updates, event changes, announcements from organizers, reminders 24h and
        2h before your events, and tasks assigned to you. When e-mail delivery is configured, the
        same messages are also sent to your inbox.
      </Typography>
      {items.length === 0 ? (
        <EmptyState message="You have no notifications yet." />
      ) : (
        <Card>
          <CardContent>
            <NotificationList items={items} onOpen={handleOpen} />
          </CardContent>
        </Card>
      )}
    </>
  );
}
