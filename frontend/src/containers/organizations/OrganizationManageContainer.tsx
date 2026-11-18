import { useCallback, useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { useParams } from 'react-router';

import DeleteIcon from '@mui/icons-material/Delete';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
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

import {
  addOrgMember,
  getOrganization,
  listOrgMembers,
  removeOrgMember,
  updateOrgMemberRole,
  updateOrganization,
} from '../../api/organizations';
import AppSnackbar from '../../components/common/AppSnackbar';
import ErrorAlert from '../../components/common/ErrorAlert';
import LoadingBox from '../../components/common/LoadingBox';
import { useAuth } from '../../context/AuthContext';
import { useApiError } from '../../hooks/useApiError';
import { useFormValidation } from '../../hooks/useFormValidation';
import { emailError, requiredText, withoutEmpty } from '../../utils/validation';
import { invalidateOrganizations } from '../../hooks/useOrganizations';
import { useSnackbar } from '../../hooks/useSnackbar';
import type { OrganizationMemberDetail, OrgRole } from '../../types';

const ROLES: { value: OrgRole; label: string }[] = [
  { value: 'ORG_ADMIN', label: 'Org admin' },
  { value: 'ORGANIZER', label: 'Organizer' },
  { value: 'MEMBER', label: 'Member' },
];

export default function OrganizationManageContainer() {
  const { orgId } = useParams<{ orgId: string }>();
  const { user, refreshUser } = useAuth();
  const { error, handleError, clearError } = useApiError();
  const { snackbar, showSnackbar, closeSnackbar } = useSnackbar();

  const [loading, setLoading] = useState(true);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [contactEmail, setContactEmail] = useState('');
  const [members, setMembers] = useState<OrganizationMemberDetail[]>([]);
  const [newEmail, setNewEmail] = useState('');
  const [newRole, setNewRole] = useState<OrgRole>('MEMBER');
  const [busy, setBusy] = useState(false);
  const profileValidation = useFormValidation<'name' | 'contact_email'>(
    withoutEmpty({
      name: requiredText(name, 'Name'),
      contact_email: emailError(contactEmail, false),
    }),
  );
  const memberValidation = useFormValidation<'email'>(
    withoutEmpty({ email: emailError(newEmail) }),
  );

  const isOrgAdmin =
    user?.global_role === 'SUPER_ADMIN' ||
    Boolean(
      user?.organization_memberships.some(
        (m) => m.organization_id === orgId && m.role === 'ORG_ADMIN',
      ),
    );

  const reloadMembers = useCallback(async () => {
    if (!orgId) return;
    setMembers(await listOrgMembers(orgId));
  }, [orgId]);

  useEffect(() => {
    if (!orgId) return;
    let ignore = false;
    Promise.all([getOrganization(orgId), listOrgMembers(orgId)])
      .then(([org, mem]) => {
        if (ignore) return;
        setName(org.name);
        setDescription(org.description ?? '');
        setContactEmail(org.contact_email ?? '');
        setMembers(mem);
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
  }, [orgId, handleError]);

  const run = async (action: () => Promise<void>, success: string) => {
    setBusy(true);
    clearError();
    try {
      await action();
      showSnackbar(success);
    } catch (err) {
      handleError(err);
    } finally {
      setBusy(false);
    }
  };

  const handleSaveProfile = (e: FormEvent) => {
    e.preventDefault();
    if (!orgId || !profileValidation.attemptSubmit()) return;
    void run(async () => {
      await updateOrganization(orgId, {
        name,
        description: description || null,
        contact_email: contactEmail || null,
      });
      invalidateOrganizations();
      await refreshUser();
    }, 'Organization profile saved.');
  };

  const handleAdd = (e: FormEvent) => {
    e.preventDefault();
    if (!orgId || !memberValidation.attemptSubmit()) return;
    void run(async () => {
      await addOrgMember(orgId, { email: newEmail.trim(), role: newRole });
      setNewEmail('');
      memberValidation.reset();
      await reloadMembers();
    }, 'Member added.');
  };

  const handleRoleChange = (member: OrganizationMemberDetail, role: OrgRole) => {
    if (!orgId) return;
    void run(async () => {
      await updateOrgMemberRole(orgId, member.user_id, role);
      await reloadMembers();
      if (member.user_id === user?.id) await refreshUser();
    }, `${member.full_name} is now ${role}.`);
  };

  const handleRemove = (member: OrganizationMemberDetail) => {
    if (!orgId || !window.confirm(`Remove ${member.full_name} from ${name}?`)) return;
    void run(async () => {
      await removeOrgMember(orgId, member.user_id);
      await reloadMembers();
      if (member.user_id === user?.id) await refreshUser();
    }, `${member.full_name} was removed.`);
  };

  if (loading) return <LoadingBox />;

  return (
    <>
      <Typography variant="h4" gutterBottom>
        {name || 'Organization'}
      </Typography>
      <ErrorAlert message={error} onClose={clearError} />

      {isOrgAdmin && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Profile
            </Typography>
            <Box
              component="form"
              onSubmit={handleSaveProfile}
              noValidate
              sx={{ maxWidth: 600 }}
            >
              <TextField
                label="Name"
                fullWidth
                margin="dense"
                required
                value={name}
                error={Boolean(profileValidation.errors.name)}
                helperText={profileValidation.errors.name}
                onChange={(e) => {
                  setName(e.target.value);
                  profileValidation.touch('name');
                }}
              />
              <TextField
                label="Description"
                fullWidth
                margin="dense"
                multiline
                minRows={2}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
              <TextField
                label="Contact e-mail"
                fullWidth
                margin="dense"
                type="email"
                value={contactEmail}
                error={Boolean(profileValidation.errors.contact_email)}
                helperText={profileValidation.errors.contact_email}
                onChange={(e) => {
                  setContactEmail(e.target.value);
                  profileValidation.touch('contact_email');
                }}
              />
              <Button type="submit" variant="contained" sx={{ mt: 1 }} disabled={busy}>
                Save profile
              </Button>
            </Box>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Members ({members.length})
          </Typography>
          {isOrgAdmin && (
            <Box
              component="form"
              onSubmit={handleAdd}
              noValidate
              display="flex"
              gap={2}
              flexWrap="wrap"
              alignItems="center"
              mb={2}
            >
              <TextField
                size="small"
                type="email"
                label="Add by e-mail"
                placeholder="student@stud.ubbcluj.ro"
                value={newEmail}
                error={Boolean(memberValidation.errors.email)}
                helperText={memberValidation.errors.email}
                onChange={(e) => {
                  setNewEmail(e.target.value);
                  memberValidation.touch('email');
                }}
                sx={{ minWidth: 280 }}
              />
              <FormControl size="small" sx={{ minWidth: 150 }}>
                <InputLabel>Role</InputLabel>
                <Select
                  value={newRole}
                  label="Role"
                  onChange={(e) => setNewRole(e.target.value as OrgRole)}
                >
                  {ROLES.map((r) => (
                    <MenuItem key={r.value} value={r.value}>
                      {r.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <Button type="submit" variant="contained" disabled={busy}>
                Add member
              </Button>
            </Box>
          )}
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>E-mail</TableCell>
                <TableCell>Role</TableCell>
                {isOrgAdmin && <TableCell align="right" />}
              </TableRow>
            </TableHead>
            <TableBody>
              {members.map((m) => (
                <TableRow key={m.user_id}>
                  <TableCell>{m.full_name}</TableCell>
                  <TableCell>{m.email}</TableCell>
                  <TableCell>
                    {isOrgAdmin ? (
                      <Select
                        size="small"
                        value={m.role}
                        disabled={busy}
                        onChange={(e) => handleRoleChange(m, e.target.value as OrgRole)}
                      >
                        {ROLES.map((r) => (
                          <MenuItem key={r.value} value={r.value}>
                            {r.label}
                          </MenuItem>
                        ))}
                      </Select>
                    ) : (
                      ROLES.find((r) => r.value === m.role)?.label
                    )}
                  </TableCell>
                  {isOrgAdmin && (
                    <TableCell align="right">
                      <Tooltip title="Remove from organization">
                        <IconButton
                          size="small"
                          color="error"
                          disabled={busy}
                          onClick={() => handleRemove(m)}
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  )}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <AppSnackbar
        open={snackbar.open}
        message={snackbar.message}
        severity={snackbar.severity}
        onClose={closeSnackbar}
      />
    </>
  );
}
