import { useEffect, useState } from 'react';

import Box from '@mui/material/Box';
import Tab from '@mui/material/Tab';
import Tabs from '@mui/material/Tabs';
import Typography from '@mui/material/Typography';

import {
  assignOrgMember,
  createOrganization,
  listOrganizations,
  updateGlobalRole,
} from '../../api/admin';
import AppSnackbar from '../../components/common/AppSnackbar';
import ErrorAlert from '../../components/common/ErrorAlert';
import LoadingBox from '../../components/common/LoadingBox';
import AssignMemberForm from '../../components/admin/AssignMemberForm';
import OrgForm from '../../components/admin/OrgForm';
import type { OrgField } from '../../components/admin/OrgForm';
import OrgList from '../../components/admin/OrgList';
import UpdateGlobalRoleForm from '../../components/admin/UpdateGlobalRoleForm';
import { useAuth } from '../../context/AuthContext';
import { ApiError } from '../../api/client';
import { useApiError } from '../../hooks/useApiError';
import { useFormValidation } from '../../hooks/useFormValidation';
import { emailError, requiredText, withoutEmpty } from '../../utils/validation';
import { useSnackbar } from '../../hooks/useSnackbar';
import { invalidateOrganizations } from '../../hooks/useOrganizations';
import type {
  AdminUserResponse,
  GlobalRole,
  OrgRole,
  OrganizationResponse,
} from '../../types';

export default function AdminContainer() {
  const [tab, setTab] = useState(0);
  const [organizations, setOrganizations] = useState<OrganizationResponse[]>([]);
  const [orgsLoading, setOrgsLoading] = useState(true);
  const { user, refreshUser } = useAuth();
  const { error, handleError, clearError } = useApiError();
  const { snackbar, showSnackbar, closeSnackbar } = useSnackbar();

  // Org Form state
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [contactEmail, setContactEmail] = useState('');
  const [formLoading, setFormLoading] = useState(false);
  const orgValidation = useFormValidation<OrgField>(
    withoutEmpty({
      name: requiredText(name, 'Organization name'),
      contact_email: emailError(contactEmail),
    }),
  );

  // Assign Member state
  const [assignOrgId, setAssignOrgId] = useState('');
  const [assignUser, setAssignUser] = useState<AdminUserResponse | null>(null);
  const [assignRole, setAssignRole] = useState<OrgRole>('ORGANIZER');
  const [assignLoading, setAssignLoading] = useState(false);

  // Update Global Role state
  const [roleUser, setRoleUser] = useState<AdminUserResponse | null>(null);
  const [globalRole, setGlobalRole] = useState<GlobalRole>('SUPER_ADMIN');
  const [roleLoading, setRoleLoading] = useState(false);

  const refreshOrgs = async () => {
    try {
      const orgs = await listOrganizations();
      setOrganizations(orgs);
      if (orgs.length > 0) {
        setAssignOrgId((prev) => prev || orgs[0].id);
      }
    } catch (err) {
      handleError(err);
    }
  };

  useEffect(() => {
    let ignore = false;
    listOrganizations()
      .then((orgs) => {
        if (!ignore) {
          setOrganizations(orgs);
          if (orgs.length > 0) {
            setAssignOrgId((prev) => prev || orgs[0].id);
          }
          setOrgsLoading(false);
        }
      })
      .catch((err) => {
        if (!ignore) {
          handleError(err);
          setOrgsLoading(false);
        }
      });
    return () => {
      ignore = true;
    };
  }, [handleError]);

  const handleCreateOrg = async () => {
    clearError();
    if (!orgValidation.attemptSubmit()) return;
    setFormLoading(true);
    try {
      await createOrganization({
        name,
        description: description || undefined,
        contact_email: contactEmail,
      });
      invalidateOrganizations();
      showSnackbar('Organization created.');
      setName('');
      setDescription('');
      setContactEmail('');
      orgValidation.reset();
      await refreshOrgs();
    } catch (err) {
      if (err instanceof ApiError && err.status === 400 && /already exists/i.test(err.detail)) {
        orgValidation.setServerErrors({ name: err.detail });
      } else if (!orgValidation.applyServerErrors(err)) {
        handleError(err);
      }
    } finally {
      setFormLoading(false);
    }
  };

  const handleAssignMember = async () => {
    if (!assignOrgId || !assignUser) return;
    setAssignLoading(true);
    clearError();
    try {
      await assignOrgMember(assignOrgId, {
        user_id: assignUser.id,
        role: assignRole,
      });
      if (user?.id === assignUser.id) {
        await refreshUser();
      }
      showSnackbar(`${assignUser.full_name} assigned as ${assignRole}.`);
      setAssignUser(null);
    } catch (err) {
      handleError(err);
    } finally {
      setAssignLoading(false);
    }
  };

  const handleUpdateGlobalRole = async () => {
    if (!roleUser) return;
    setRoleLoading(true);
    clearError();
    try {
      const updated = await updateGlobalRole(roleUser.id, {
        global_role: globalRole,
      });
      if (user?.id === roleUser.id) {
        await refreshUser();
      }
      showSnackbar(
        `Updated ${updated.full_name} (${updated.email}) to ${updated.global_role}.`,
      );
      setRoleUser(null);
    } catch (err) {
      handleError(err);
    } finally {
      setRoleLoading(false);
    }
  };

  return (
    <>
      <Typography variant="h4" gutterBottom>
        Admin Panel
      </Typography>

      <Tabs value={tab} onChange={(_, v: number) => setTab(v)} sx={{ mb: 3 }}>
        <Tab label="Organizations" />
        <Tab label="Create Organization" />
        <Tab label="Assign Membership" />
        <Tab label="Update Global Role" />
      </Tabs>

      <ErrorAlert message={error} onClose={clearError} />

      {tab === 0 &&
        (orgsLoading ? (
          <LoadingBox />
        ) : (
          <OrgList organizations={organizations} />
        ))}

      {tab === 1 && (
        <Box>
          <OrgForm
            name={name}
            description={description}
            contactEmail={contactEmail}
            error={error}
            fieldErrors={orgValidation.errors}
            loading={formLoading}
            onNameChange={(v) => {
              setName(v);
              orgValidation.touch('name');
            }}
            onDescriptionChange={setDescription}
            onContactEmailChange={(v) => {
              setContactEmail(v);
              orgValidation.touch('contact_email');
            }}
            onSubmit={handleCreateOrg}
            onClearError={clearError}
          />
        </Box>
      )}

      {tab === 2 && (
        <Box>
          <AssignMemberForm
            organizations={organizations}
            orgId={assignOrgId}
            selectedUser={assignUser}
            role={assignRole}
            error={error}
            loading={assignLoading}
            onOrgIdChange={setAssignOrgId}
            onUserChange={setAssignUser}
            onRoleChange={setAssignRole}
            onSubmit={handleAssignMember}
            onClearError={clearError}
          />
        </Box>
      )}

      {tab === 3 && (
        <Box>
          <UpdateGlobalRoleForm
            selectedUser={roleUser}
            globalRole={globalRole}
            error={error}
            loading={roleLoading}
            onUserChange={setRoleUser}
            onGlobalRoleChange={setGlobalRole}
            onSubmit={handleUpdateGlobalRole}
            onClearError={clearError}
          />
        </Box>
      )}

      <AppSnackbar
        open={snackbar.open}
        message={snackbar.message}
        severity={snackbar.severity}
        onClose={closeSnackbar}
      />
    </>
  );
}
