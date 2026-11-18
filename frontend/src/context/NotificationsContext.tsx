import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';

import { getNotifications, markAllNotificationsRead, markNotificationRead } from '../api/me';
import type { NotificationItem } from '../types';
import { useAuth } from './AuthContext';

const POLL_INTERVAL_MS = 30_000;

interface NotificationsState {
  items: NotificationItem[];
  unreadCount: number;
  refresh: () => Promise<void>;
  markRead: (id: string) => Promise<void>;
  markAllRead: () => Promise<void>;
}

const NotificationsContext = createContext<NotificationsState | undefined>(undefined);

export function NotificationsProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);

  const refresh = useCallback(async () => {
    try {
      const res = await getNotifications(false, 30);
      setItems(res.items);
      setUnreadCount(res.unread_count);
    } catch {
      // Polling is best-effort; a 401 is handled globally by the API client.
    }
  }, []);

  useEffect(() => {
    if (!user) return;
    let ignore = false;
    const load = () => {
      getNotifications(false, 30)
        .then((res) => {
          if (!ignore) {
            setItems(res.items);
            setUnreadCount(res.unread_count);
          }
        })
        .catch(() => {});
    };
    load();
    const timer = window.setInterval(load, POLL_INTERVAL_MS);
    return () => {
      ignore = true;
      window.clearInterval(timer);
      setItems([]);
      setUnreadCount(0);
    };
  }, [user]);

  const markRead = useCallback(async (id: string) => {
    const updated = await markNotificationRead(id);
    setItems((prev) => {
      const wasUnread = prev.some((n) => n.id === id && !n.read_at);
      if (wasUnread) setUnreadCount((c) => Math.max(c - 1, 0));
      return prev.map((n) => (n.id === id ? updated : n));
    });
  }, []);

  const markAllRead = useCallback(async () => {
    await markAllNotificationsRead();
    const now = new Date().toISOString();
    setItems((prev) => prev.map((n) => (n.read_at ? n : { ...n, read_at: now })));
    setUnreadCount(0);
  }, []);

  const value = useMemo(
    () => ({ items, unreadCount, refresh, markRead, markAllRead }),
    [items, unreadCount, refresh, markRead, markAllRead],
  );

  return <NotificationsContext value={value}>{children}</NotificationsContext>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useNotifications(): NotificationsState {
  const ctx = useContext(NotificationsContext);
  if (!ctx) throw new Error('useNotifications must be used within NotificationsProvider');
  return ctx;
}
