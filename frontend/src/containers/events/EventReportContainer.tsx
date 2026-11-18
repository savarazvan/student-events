import { useEffect, useState } from 'react';

import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Divider from '@mui/material/Divider';
import LinearProgress from '@mui/material/LinearProgress';
import Rating from '@mui/material/Rating';
import Typography from '@mui/material/Typography';

import { getEventReport } from '../../api/events';
import ErrorAlert from '../../components/common/ErrorAlert';
import LoadingBox from '../../components/common/LoadingBox';
import AttendanceStats from '../../components/events/AttendanceStats';
import { useApiError } from '../../hooks/useApiError';
import type { EventReportResponse } from '../../types';

interface Props {
  eventId: string;
}

export default function EventReportContainer({ eventId }: Props) {
  const [report, setReport] = useState<EventReportResponse | null>(null);
  const { error, handleError } = useApiError();

  useEffect(() => {
    let ignore = false;
    getEventReport(eventId)
      .then((res) => {
        if (!ignore) setReport(res);
      })
      .catch((err) => {
        if (!ignore) handleError(err);
      });
    return () => {
      ignore = true;
    };
  }, [eventId, handleError]);

  if (error) return <ErrorAlert message={error} />;
  if (!report) return <LoadingBox />;

  const maxCount = Math.max(1, ...Object.values(report.rating_distribution));

  return (
    <>
      <AttendanceStats stats={report.attendance} />
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Participant feedback
          </Typography>
          {report.feedback_count === 0 ? (
            <Typography variant="body2" color="text.secondary">
              {report.status === 'COMPLETED'
                ? 'No feedback yet. Attendees who checked in were asked to rate the event.'
                : 'Feedback opens for checked-in attendees once the event is marked COMPLETED.'}
            </Typography>
          ) : (
            <>
              <Box display="flex" alignItems="center" gap={2} mb={2} flexWrap="wrap">
                <Typography variant="h3" fontWeight="bold">
                  {report.average_rating?.toFixed(2)}
                </Typography>
                <Box>
                  <Rating value={report.average_rating ?? 0} precision={0.1} readOnly />
                  <Typography variant="body2" color="text.secondary">
                    {report.feedback_count} ratings ·{' '}
                    {(report.feedback_response_rate * 100).toFixed(0)}% of attendees answered
                  </Typography>
                </Box>
              </Box>
              {[5, 4, 3, 2, 1].map((stars) => {
                const count = report.rating_distribution[String(stars)] ?? 0;
                return (
                  <Box key={stars} display="flex" alignItems="center" gap={1} mb={0.5}>
                    <Typography variant="body2" width={52}>
                      {stars} ★
                    </Typography>
                    <LinearProgress
                      variant="determinate"
                      value={(count / maxCount) * 100}
                      sx={{ flex: 1, height: 8, borderRadius: 4 }}
                    />
                    <Typography variant="body2" width={28} textAlign="right">
                      {count}
                    </Typography>
                  </Box>
                );
              })}
              {report.comments.length > 0 && (
                <>
                  <Divider sx={{ my: 2 }} />
                  <Typography variant="subtitle1" gutterBottom>
                    Comments (anonymous)
                  </Typography>
                  {report.comments.map((c, i) => (
                    <Box key={i} mb={1.5}>
                      <Rating value={c.rating} size="small" readOnly />
                      <Typography variant="body2" sx={{ whiteSpace: 'pre-line' }}>
                        {c.comment}
                      </Typography>
                    </Box>
                  ))}
                </>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </>
  );
}
