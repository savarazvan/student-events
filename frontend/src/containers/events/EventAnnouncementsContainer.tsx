import { useCallback, useEffect, useState } from 'react';
import type { FormEvent } from 'react';

import CampaignIcon from '@mui/icons-material/Campaign';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Divider from '@mui/material/Divider';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';

import { createAnnouncement, listAnnouncements } from '../../api/events';
import ErrorAlert from '../../components/common/ErrorAlert';
import { useApiError } from '../../hooks/useApiError';
import type { AnnouncementResponse } from '../../types';
import { timeAgo } from '../../utils/time';

interface Props {
  eventId: string;
  canPost: boolean;
  onPosted?: (recipients: number) => void;
}

export default function EventAnnouncementsContainer({ eventId, canPost, onPosted }: Props) {
  const [items, setItems] = useState<AnnouncementResponse[]>([]);
  const [title, setTitle] = useState('');
  const [message, setMessage] = useState('');
  const [sending, setSending] = useState(false);
  const { error, handleError, clearError } = useApiError();

  const load = useCallback(() => listAnnouncements(eventId), [eventId]);

  useEffect(() => {
    let ignore = false;
    load()
      .then((res) => {
        if (!ignore) setItems(res);
      })
      .catch(() => {});
    return () => {
      ignore = true;
    };
  }, [load]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSending(true);
    clearError();
    try {
      const created = await createAnnouncement(eventId, { title, message });
      setTitle('');
      setMessage('');
      setItems(await load());
      onPosted?.(created.recipients ?? 0);
    } catch (err) {
      handleError(err);
    } finally {
      setSending(false);
    }
  };

  if (!canPost && items.length === 0) return null;

  return (
    <Card sx={{ mt: 2 }}>
      <CardContent>
        <Box display="flex" alignItems="center" gap={1} mb={1}>
          <CampaignIcon color="primary" />
          <Typography variant="h6">Announcements</Typography>
        </Box>

        {canPost && (
          <Box component="form" onSubmit={handleSubmit} mb={2}>
            <ErrorAlert message={error} onClose={clearError} />
            <TextField
              label="Title"
              fullWidth
              size="small"
              margin="dense"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              slotProps={{ htmlInput: { maxLength: 255 } }}
            />
            <TextField
              label="Message to all registered participants"
              fullWidth
              size="small"
              margin="dense"
              required
              multiline
              minRows={2}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              slotProps={{ htmlInput: { maxLength: 5000 } }}
            />
            <Button
              type="submit"
              variant="contained"
              disabled={sending || !title.trim() || !message.trim()}
              sx={{ mt: 1 }}
            >
              {sending ? 'Sending…' : 'Send announcement'}
            </Button>
            <Typography variant="caption" color="text.secondary" display="block" mt={0.5}>
              Confirmed and waitlisted participants get an in-app notification (and an e-mail when e-mail
              delivery is configured).
            </Typography>
          </Box>
        )}

        {items.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            No announcements yet.
          </Typography>
        ) : (
          items.map((a, i) => (
            <Box key={a.id}>
              {i > 0 && <Divider sx={{ my: 1.5 }} />}
              <Typography variant="subtitle1" fontWeight="bold">
                {a.title}
              </Typography>
              <Typography variant="body2" sx={{ whiteSpace: 'pre-line' }}>
                {a.message}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {a.author_name} · {timeAgo(a.created_at)}
              </Typography>
            </Box>
          ))
        )}
      </CardContent>
    </Card>
  );
}
