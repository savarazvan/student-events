import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Typography from '@mui/material/Typography';
import LinearProgress from '@mui/material/LinearProgress';

import type { AttendanceStatsResponse } from '../../types';

interface Props {
  stats: AttendanceStatsResponse;
}

export default function AttendanceStats({ stats }: Props) {
  return (
    <Card sx={{ mb: 2 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Attendance Overview
        </Typography>
        <Box display="flex" flexWrap="wrap" gap={3} mb={2}>
          <Stat label="Confirmed" value={stats.confirmed} />
          <Stat label="Waitlisted" value={stats.waitlisted} />
          <Stat label="Cancelled" value={stats.cancelled} />
          <Stat label="Checked In" value={stats.checked_in} />
          <Stat label="Not Checked In" value={stats.not_checked_in} />
          <Stat label="Spots Left" value={stats.spots_left} />
        </Box>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          Attendance rate: {(stats.attendance_rate * 100).toFixed(1)}%
        </Typography>
        <LinearProgress
          variant="determinate"
          value={stats.attendance_rate * 100}
          sx={{ height: 8, borderRadius: 4 }}
        />
      </CardContent>
    </Card>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <Box>
      <Typography variant="h5" fontWeight="bold">
        {value}
      </Typography>
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
    </Box>
  );
}
