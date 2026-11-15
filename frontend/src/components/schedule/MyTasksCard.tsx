import { useEffect, useState } from 'react';

import AssignmentIcon from '@mui/icons-material/Assignment';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import List from '@mui/material/List';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemText from '@mui/material/ListItemText';
import Typography from '@mui/material/Typography';

import { getMyTasks } from '../../api/me';
import type { MyTask } from '../../types';

interface Props {
  onOpenEvent: (eventId: string) => void;
}

/** Open organizing tasks assigned to the user; hidden when there are none. */
export default function MyTasksCard({ onOpenEvent }: Props) {
  const [tasks, setTasks] = useState<MyTask[]>([]);

  useEffect(() => {
    let ignore = false;
    getMyTasks()
      .then((res) => {
        if (!ignore) setTasks(res);
      })
      .catch(() => {});
    return () => {
      ignore = true;
    };
  }, []);

  if (tasks.length === 0) return null;

  return (
    <Card sx={{ mb: 3 }}>
      <CardContent>
        <Box display="flex" alignItems="center" gap={1} mb={1}>
          <AssignmentIcon color="secondary" />
          <Typography variant="h6">My organizing tasks</Typography>
        </Box>
        <List dense disablePadding>
          {tasks.map((t) => (
            <ListItemButton key={t.id} onClick={() => onOpenEvent(t.event.id)}>
              <ListItemText
                primary={t.title}
                secondary={`${t.event.title}${
                  t.due_at
                    ? ` · due ${new Date(t.due_at).toLocaleString(undefined, {
                        dateStyle: 'medium',
                        timeStyle: 'short',
                      })}`
                    : ''
                }`}
              />
              <Chip
                size="small"
                label={t.status === 'IN_PROGRESS' ? 'In progress' : 'To do'}
                color={t.status === 'IN_PROGRESS' ? 'info' : 'default'}
              />
            </ListItemButton>
          ))}
        </List>
      </CardContent>
    </Card>
  );
}
