import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';

import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Rating from '@mui/material/Rating';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';

import { getMyFeedback, submitFeedback } from '../../api/events';
import ErrorAlert from '../../components/common/ErrorAlert';
import { useApiError } from '../../hooks/useApiError';

interface Props {
  eventId: string;
  onSaved?: () => void;
}

/** Shown to attendees who checked in, once the event is COMPLETED. */
export default function EventFeedbackContainer({ eventId, onSaved }: Props) {
  const [rating, setRating] = useState<number | null>(null);
  const [comment, setComment] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [saving, setSaving] = useState(false);
  const { error, handleError, clearError } = useApiError();

  useEffect(() => {
    let ignore = false;
    getMyFeedback(eventId)
      .then((fb) => {
        if (ignore) return;
        setRating(fb.rating);
        setComment(fb.comment ?? '');
        setSubmitted(true);
      })
      .catch(() => {
        // 404: no feedback yet.
      });
    return () => {
      ignore = true;
    };
  }, [eventId]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!rating) return;
    setSaving(true);
    clearError();
    try {
      await submitFeedback(eventId, { rating, comment: comment || null });
      setSubmitted(true);
      onSaved?.();
    } catch (err) {
      handleError(err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card sx={{ mt: 2 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          {submitted ? 'Your feedback' : 'How was the event?'}
        </Typography>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          Your rating is anonymous for the organizers and helps them plan better events.
        </Typography>
        <ErrorAlert message={error} onClose={clearError} />
        <Box component="form" onSubmit={handleSubmit}>
          <Rating
            value={rating}
            size="large"
            onChange={(_, value) => setRating(value)}
            sx={{ my: 1 }}
          />
          <TextField
            label="Comment (optional)"
            fullWidth
            multiline
            minRows={2}
            size="small"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            slotProps={{ htmlInput: { maxLength: 2000 } }}
          />
          <Button type="submit" variant="contained" disabled={saving || !rating} sx={{ mt: 1 }}>
            {submitted ? 'Update feedback' : 'Send feedback'}
          </Button>
        </Box>
      </CardContent>
    </Card>
  );
}
