import { useCallback, useEffect, useState } from 'react';
import type { FormEvent } from 'react';

import DeleteIcon from '@mui/icons-material/Delete';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import FormControl from '@mui/material/FormControl';
import IconButton from '@mui/material/IconButton';
import InputLabel from '@mui/material/InputLabel';
import MenuItem from '@mui/material/MenuItem';
import Select from '@mui/material/Select';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import TextField from '@mui/material/TextField';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';

import { createTask, deleteTask, listTasks, updateTask } from '../../api/events';
import { listOrgMembers } from '../../api/organizations';
import EmptyState from '../../components/common/EmptyState';
import ErrorAlert from '../../components/common/ErrorAlert';
import LoadingBox from '../../components/common/LoadingBox';
import { useApiError } from '../../hooks/useApiError';
import type {
  EventResponse,
  EventTask,
  EventTaskStatus,
  OrganizationMemberDetail,
} from '../../types';

const STATUS_LABEL: Record<EventTaskStatus, string> = {
  TODO: 'To do',
  IN_PROGRESS: 'In progress',
  DONE: 'Done',
};
const STATUS_COLOR: Record<EventTaskStatus, 'default' | 'info' | 'success'> = {
  TODO: 'default',
  IN_PROGRESS: 'info',
  DONE: 'success',
};

interface Props {
  event: EventResponse;
  currentUserId: string;
  canPlan: boolean;
}

export default function EventTeamContainer({ event, currentUserId, canPlan }: Props) {
  const [tasks, setTasks] = useState<EventTask[]>([]);
  const [members, setMembers] = useState<OrganizationMemberDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [assigneeId, setAssigneeId] = useState('');
  const [dueAt, setDueAt] = useState('');
  const [busy, setBusy] = useState(false);
  const { error, handleError, clearError } = useApiError();
  const isFinal = event.status === 'COMPLETED' || event.status === 'CANCELLED';

  const reload = useCallback(async () => setTasks(await listTasks(event.id)), [event.id]);

  useEffect(() => {
    let ignore = false;
    Promise.all([listTasks(event.id), listOrgMembers(event.organization_id)])
      .then(([t, m]) => {
        if (ignore) return;
        setTasks(t);
        setMembers(m);
        setLoading(false);
      })
      .catch((err) => {
        if (!ignore) {
          handleError(err);
          setLoading(false);
        }
      });
    return () => {
      ignore = true;
    };
  }, [event.id, event.organization_id, handleError]);

  const run = async (action: () => Promise<unknown>) => {
    setBusy(true);
    clearError();
    try {
      await action();
      await reload();
    } catch (err) {
      handleError(err);
    } finally {
      setBusy(false);
    }
  };

  const handleCreate = (e: FormEvent) => {
    e.preventDefault();
    void run(async () => {
      await createTask(event.id, {
        title,
        description: description || null,
        assignee_id: assigneeId || null,
        due_at: dueAt ? new Date(dueAt).toISOString() : null,
      });
      setTitle('');
      setDescription('');
      setAssigneeId('');
      setDueAt('');
    });
  };

  if (loading) return <LoadingBox />;

  return (
    <>
      <ErrorAlert message={error} onClose={clearError} />
      {canPlan && !isFinal && (
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              New task
            </Typography>
            <Box
              component="form"
              onSubmit={handleCreate}
              display="flex"
              gap={2}
              flexWrap="wrap"
              alignItems="flex-start"
            >
              <TextField
                size="small"
                label="Responsibility"
                placeholder="e.g. Check-in desk"
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                sx={{ minWidth: 220, flex: 1 }}
              />
              <FormControl size="small" sx={{ minWidth: 200 }}>
                <InputLabel>Assignee</InputLabel>
                <Select
                  value={assigneeId}
                  label="Assignee"
                  onChange={(e) => setAssigneeId(e.target.value)}
                >
                  <MenuItem value="">Unassigned</MenuItem>
                  {members.map((m) => (
                    <MenuItem key={m.user_id} value={m.user_id}>
                      {m.full_name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <TextField
                size="small"
                label="Due"
                type="datetime-local"
                value={dueAt}
                onChange={(e) => setDueAt(e.target.value)}
                slotProps={{ inputLabel: { shrink: true } }}
              />
              <TextField
                size="small"
                label="Details (optional)"
                fullWidth
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
              <Button type="submit" variant="contained" disabled={busy || !title.trim()}>
                Add task
              </Button>
            </Box>
          </CardContent>
        </Card>
      )}

      {tasks.length === 0 ? (
        <EmptyState message="No tasks planned for this event yet." />
      ) : (
        <Card>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Task</TableCell>
                <TableCell>Assignee</TableCell>
                <TableCell>Due</TableCell>
                <TableCell>Status</TableCell>
                {canPlan && <TableCell />}
              </TableRow>
            </TableHead>
            <TableBody>
              {tasks.map((t) => {
                const canChangeStatus = canPlan || t.assignee_id === currentUserId;
                return (
                  <TableRow key={t.id}>
                    <TableCell>
                      <Typography variant="body2" fontWeight="medium">
                        {t.title}
                      </Typography>
                      {t.description && (
                        <Typography variant="caption" color="text.secondary">
                          {t.description}
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      {canPlan ? (
                        <Select
                          size="small"
                          value={t.assignee_id ?? ''}
                          disabled={busy}
                          displayEmpty
                          onChange={(e) =>
                            void run(() =>
                              updateTask(event.id, t.id, { assignee_id: e.target.value || null }),
                            )
                          }
                        >
                          <MenuItem value="">Unassigned</MenuItem>
                          {members.map((m) => (
                            <MenuItem key={m.user_id} value={m.user_id}>
                              {m.full_name}
                            </MenuItem>
                          ))}
                        </Select>
                      ) : (
                        (t.assignee_name ?? '—')
                      )}
                    </TableCell>
                    <TableCell>
                      {t.due_at
                        ? new Date(t.due_at).toLocaleString(undefined, {
                            dateStyle: 'short',
                            timeStyle: 'short',
                          })
                        : '—'}
                    </TableCell>
                    <TableCell>
                      {canChangeStatus ? (
                        <Select
                          size="small"
                          value={t.status}
                          disabled={busy}
                          onChange={(e) =>
                            void run(() =>
                              updateTask(event.id, t.id, {
                                status: e.target.value as EventTaskStatus,
                              }),
                            )
                          }
                        >
                          {(Object.keys(STATUS_LABEL) as EventTaskStatus[]).map((s) => (
                            <MenuItem key={s} value={s}>
                              {STATUS_LABEL[s]}
                            </MenuItem>
                          ))}
                        </Select>
                      ) : (
                        <Chip
                          size="small"
                          label={STATUS_LABEL[t.status]}
                          color={STATUS_COLOR[t.status]}
                        />
                      )}
                    </TableCell>
                    {canPlan && (
                      <TableCell align="right">
                        <Tooltip title="Delete task">
                          <IconButton
                            size="small"
                            color="error"
                            disabled={busy}
                            onClick={() => void run(() => deleteTask(event.id, t.id))}
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </TableCell>
                    )}
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </Card>
      )}
    </>
  );
}
