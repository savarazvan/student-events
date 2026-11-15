import { useState } from 'react';
import AccountCircleIcon from '@mui/icons-material/AccountCircle';
import AdminPanelSettingsIcon from '@mui/icons-material/AdminPanelSettings';
import CalendarMonthIcon from '@mui/icons-material/CalendarMonth';
import EventIcon from '@mui/icons-material/Event';
import LogoutIcon from '@mui/icons-material/Logout';
import LoginIcon from '@mui/icons-material/Login';
import PersonAddIcon from '@mui/icons-material/PersonAdd';
import AppBar from '@mui/material/AppBar';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import Divider from '@mui/material/Divider';
import IconButton from '@mui/material/IconButton';
import Toolbar from '@mui/material/Toolbar';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import { useNavigate } from 'react-router';

import { useAuth } from '../../context/AuthContext';

export default function Navbar() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const [profileOpen, setProfileOpen] = useState(false);

  const handleLogout = () => {
    signOut();
    navigate('/login');
  };

  return (
    <>
      <AppBar position="static">
        <Toolbar>
          <EventIcon sx={{ mr: 1 }} />
          <Typography
            variant="h6"
            component="div"
            sx={{ cursor: 'pointer', mr: 2 }}
            onClick={() => navigate('/')}
          >
            UBB Events
          </Typography>

          <Box sx={{ flexGrow: 1, display: 'flex', gap: 1 }}>
            <Button color="inherit" onClick={() => navigate('/events')}>
              Events
            </Button>
            {user && (
              <Button
                color="inherit"
                startIcon={<CalendarMonthIcon />}
                onClick={() => navigate('/my-schedule')}
              >
                My Schedule
              </Button>
            )}
            {user?.global_role === 'SUPER_ADMIN' && (
              <Button
                color="inherit"
                startIcon={<AdminPanelSettingsIcon />}
                onClick={() => navigate('/admin')}
              >
                Admin
              </Button>
            )}
          </Box>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {user ? (
              <>
                <Button
                  color="inherit"
                  startIcon={<AccountCircleIcon />}
                  onClick={() => setProfileOpen(true)}
                  sx={{ textTransform: 'none' }}
                >
                  {user.full_name}
                </Button>
                <Tooltip title="Logout">
                  <IconButton color="inherit" onClick={handleLogout}>
                    <LogoutIcon />
                  </IconButton>
                </Tooltip>
              </>
            ) : (
              <>
                <Button
                  color="inherit"
                  startIcon={<LoginIcon />}
                  onClick={() => navigate('/login')}
                >
                  Login
                </Button>
                <Button
                  color="inherit"
                  startIcon={<PersonAddIcon />}
                  onClick={() => navigate('/register')}
                >
                  Register
                </Button>
              </>
            )}
          </Box>
        </Toolbar>
      </AppBar>

      {user && (
        <Dialog
          open={profileOpen}
          onClose={() => setProfileOpen(false)}
          maxWidth="sm"
          fullWidth
        >
          <DialogTitle>User Profile</DialogTitle>
          <DialogContent dividers>
            <Typography variant="subtitle1" fontWeight="bold">
              {user.full_name}
            </Typography>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              {user.email}
            </Typography>
            <Box display="flex" alignItems="center" gap={1} mt={1} mb={2}>
              <Chip
                label={user.global_role}
                size="small"
                color={user.global_role === 'SUPER_ADMIN' ? 'secondary' : 'default'}
              />
              <Chip
                label={user.is_active ? 'Active' : 'Inactive'}
                size="small"
                color={user.is_active ? 'success' : 'error'}
                variant="outlined"
              />
            </Box>
            <Typography variant="caption" color="text.secondary" display="block">
              User ID (UUID)
            </Typography>
            <Typography
              variant="body2"
              sx={{
                fontFamily: 'monospace',
                bgcolor: 'action.hover',
                p: 1,
                borderRadius: 1,
                mt: 0.5,
                mb: 2,
                wordBreak: 'break-all',
              }}
            >
              {user.id}
            </Typography>

            <Divider sx={{ my: 1.5 }} />
            <Typography variant="subtitle2" gutterBottom>
              Organization Memberships
            </Typography>
            {user.organization_memberships.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                No organization memberships assigned.
              </Typography>
            ) : (
              user.organization_memberships.map((m) => (
                <Box
                  key={m.organization_id}
                  display="flex"
                  justifyContent="space-between"
                  alignItems="center"
                  py={0.75}
                >
                  <Box>
                    <Typography variant="body2" fontWeight="medium">
                      {m.organization_name}
                    </Typography>
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{ fontFamily: 'monospace' }}
                    >
                      {m.organization_id}
                    </Typography>
                  </Box>
                  <Chip label={m.role} size="small" color="primary" variant="outlined" />
                </Box>
              ))
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setProfileOpen(false)}>Close</Button>
          </DialogActions>
        </Dialog>
      )}
    </>
  );
}
