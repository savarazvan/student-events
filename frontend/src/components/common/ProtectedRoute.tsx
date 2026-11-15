import CircularProgress from '@mui/material/CircularProgress';
import Box from '@mui/material/Box';
import { Navigate, Outlet } from 'react-router';

import { useAuth } from '../../context/AuthContext';
import type { GlobalRole } from '../../types';

interface Props {
  requiredRole?: GlobalRole;
}

export default function ProtectedRoute({ requiredRole }: Props) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" mt={10}>
        <CircularProgress />
      </Box>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (requiredRole && user.global_role !== requiredRole) {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}
