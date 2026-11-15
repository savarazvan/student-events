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
import OrgList from '../../components/admin/OrgList';
import UpdateGlobalRoleForm from '../../components/admin/UpdateGlobalRoleForm';
import { useAuth } from '../../context/AuthContext';
import { useApiError } from '../../hooks/useApiError';
import { useSnackbar } from '../../hooks/useSnackbar';
import type { GlobalRole, OrgRole, OrganizationResponse } from '../../types';

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

  // Assign Member state
  const [assignOrgId, setAssignOrgId] = useState('');
  const [assignUserId, setAssignUserId] = useState('');
  const [assignRole, setAssignRole] = useState<OrgRole>('ORGANIZER');
  const [assignLoading, setAssignLoading] = useState(false);

  // Update Global Role state
  const [roleUserId, setRoleUserId] = useState('');
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
    setFormLoading(true);
    clearError();
    try {
      await createOrganization({
        name,
        description: description || undefined,
        contact_email: contactEmail,
      });
      showSnackbar('Organization created.');
      setName('');
      setDescription('');
      setContactEmail('');
      await refreshOrgs();
    } catch (err) {
      handleError(err);
    } finally {
      setFormLoading(false);
    }
  };

  const handleAssignMember = async () => {
    if (!assignOrgId || !assignUserId) return;
    setAssignLoading(true);
    clearError();
    try {
      await assignOrgMember(assignOrgId, {
        user_id: assignUserId,
        role: assignRole,
      });
      if (user?.id === assignUserId) {
        await refreshUser();
      }
      showSnackbar('Member assigned successfully.');
      setAssignUserId('');
    } catch (err) {
      handleError(err);
    } finally {
      setAssignLoading(false);
    }
  };

  const handleUpdateGlobalRole = async () => {
    if (!roleUserId) return;
    setRoleLoading(true);
    clearError();
    try {
      const updated = await updateGlobalRole(roleUserId, {
        global_role: globalRole,
      });
      if (user?.id === roleUserId) {
        await refreshUser();
      }
      showSnackbar(
        `Updated ${updated.full_name} (${updated.email}) to ${updated.global_role}.`,
      );
      setRoleUserId('');
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
            loading={formLoading}
            onNameChange={setName}
            onDescriptionChange={setDescription}
            onContactEmailChange={setContactEmail}
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
            userId={assignUserId}
            role={assignRole}
            error={error}
            loading={assignLoading}
            onOrgIdChange={setAssignOrgId}
            onUserIdChange={setAssignUserId}
            onRoleChange={setAssignRole}
            onSubmit={handleAssignMember}
            onClearError={clearError}
          />
        </Box>
      )}

      {tab === 3 && (
        <Box>
          <UpdateGlobalRoleForm
            userId={roleUserId}
            globalRole={globalRole}
            error={error}
            loading={roleLoading}
            onUserIdChange={setRoleUserId}
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
