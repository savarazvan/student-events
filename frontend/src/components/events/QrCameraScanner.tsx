import { useEffect, useRef, useState } from 'react';
import QrScanner from 'qr-scanner';

import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import Typography from '@mui/material/Typography';

export interface ScanOutcome {
  ok: boolean;
  message: string;
}

interface Props {
  open: boolean;
  onClose: () => void;
  /** Called for every new QR code; the outcome is shown to the person at the door. */
  onScan: (token: string) => Promise<ScanOutcome>;
}

// Ignore the same code while it stays in front of the camera.
const SAME_CODE_COOLDOWN_MS = 4000;

export default function QrCameraScanner({ open, onClose, onScan }: Props) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [outcome, setOutcome] = useState<ScanOutcome | null>(null);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const onScanRef = useRef(onScan);

  useEffect(() => {
    onScanRef.current = onScan;
  }, [onScan]);

  useEffect(() => {
    if (!open) return;
    let scanner: QrScanner | null = null;
    let busy = false;
    let last = { token: '', at: 0 };
    let cancelled = false;

    // The <video> element mounts with the dialog; wait one frame for it.
    const frame = requestAnimationFrame(() => {
      if (cancelled || !videoRef.current) return;
      scanner = new QrScanner(
        videoRef.current,
        (result) => {
          const token = result.data.trim();
          const now = Date.now();
          if (busy || !token || (token === last.token && now - last.at < SAME_CODE_COOLDOWN_MS)) {
            return;
          }
          busy = true;
          last = { token, at: now };
          onScanRef
            .current(token)
            .then(setOutcome)
            .finally(() => {
              busy = false;
            });
        },
        { preferredCamera: 'environment', highlightScanRegion: true, highlightCodeOutline: true },
      );
      scanner.start().catch((err: unknown) => {
        setCameraError(
          err instanceof Error
            ? err.message
            : 'Camera unavailable. Allow camera access (HTTPS or localhost is required).',
        );
      });
    });

    return () => {
      cancelled = true;
      cancelAnimationFrame(frame);
      scanner?.stop();
      scanner?.destroy();
    };
  }, [open]);

  const handleClose = () => {
    setOutcome(null);
    setCameraError(null);
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Scan tickets</DialogTitle>
      <DialogContent>
        {cameraError ? (
          <Alert severity="error">{String(cameraError)}</Alert>
        ) : (
          <Box
            sx={{
              position: 'relative',
              width: '100%',
              bgcolor: 'black',
              borderRadius: 1,
              overflow: 'hidden',
            }}
          >
            <video ref={videoRef} style={{ width: '100%', display: 'block' }} muted playsInline />
          </Box>
        )}
        <Box mt={2} minHeight={56}>
          {outcome ? (
            <Alert severity={outcome.ok ? 'success' : 'error'} variant="filled">
              {outcome.message}
            </Alert>
          ) : (
            <Typography variant="body2" color="text.secondary">
              Point the camera at the attendee&apos;s QR ticket. Scanning continues automatically
              for the next person.
            </Typography>
          )}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>Done</Button>
      </DialogActions>
    </Dialog>
  );
}
