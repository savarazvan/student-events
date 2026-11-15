import Alert from '@mui/material/Alert';

interface Props {
  message: string | null;
  onClose?: () => void;
}

export default function ErrorAlert({ message, onClose }: Props) {
  if (!message) return null;
  return (
    <Alert severity="error" onClose={onClose} sx={{ mb: 2 }}>
      {message}
    </Alert>
  );
}
