import PhotoCameraIcon from '@mui/icons-material/PhotoCamera';
import QrCodeScannerIcon from '@mui/icons-material/QrCodeScanner';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import InputAdornment from '@mui/material/InputAdornment';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import type { FormEvent } from 'react';

interface Props {
  token: string;
  loading: boolean;
  disabled?: boolean;
  onTokenChange: (v: string) => void;
  onSubmit: () => void;
  onOpenCamera: () => void;
}

export default function QrCheckInForm({
  token,
  loading,
  disabled,
  onTokenChange,
  onSubmit,
  onOpenCamera,
}: Props) {
  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!token.trim() || disabled) return;
    onSubmit();
  };

  return (
    <Card sx={{ mb: 2 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          QR Check-In
        </Typography>
        <Button
          variant="contained"
          startIcon={<PhotoCameraIcon />}
          disabled={disabled}
          onClick={onOpenCamera}
          sx={{ mb: 2 }}
        >
          Scan with camera
        </Button>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          Or paste the token printed under the attendee&apos;s QR code (or from a USB scanner):
        </Typography>
        <Box
          component="form"
          onSubmit={handleSubmit}
          display="flex"
          gap={2}
          alignItems="center"
          flexWrap="wrap"
        >
          <TextField
            size="small"
            placeholder="Scan or paste attendee QR token…"
            value={token}
            disabled={disabled || loading}
            onChange={(e) => onTokenChange(e.target.value)}
            slotProps={{
              input: {
                startAdornment: (
                  <InputAdornment position="start">
                    <QrCodeScannerIcon />
                  </InputAdornment>
                ),
              },
            }}
            sx={{ flexGrow: 1, minWidth: 260 }}
          />
          <Button
            type="submit"
            variant="contained"
            disabled={disabled || loading || !token.trim()}
          >
            {loading ? 'Checking in…' : 'Check In by Token'}
          </Button>
        </Box>
        {disabled && (
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
            Check-in is only enabled when the event is PUBLISHED or IN_PROGRESS.
          </Typography>
        )}
      </CardContent>
    </Card>
  );
}
