import { useEffect, useState } from "react";
import { Bell, CheckCircle2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { authGet, authPost } from "@/lib/api";


export default function NotificationCenter({ user }) {
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);

  const loadNotifications = async () => {
    const response = await authGet("/notifications?status=all");
    setNotifications(response.items || []);
    setUnreadCount(response.unread_count || 0);
  };

  useEffect(() => {
    loadNotifications();
    const interval = window.setInterval(loadNotifications, 20000);
    return () => window.clearInterval(interval);
  }, [user?.id]);

  const markRead = async (notificationId) => {
    await authPost(`/notifications/${notificationId}/read`, {});
    await loadNotifications();
  };

  return (
    <div className="relative">
      <Button
        type="button"
        variant="outline"
        onClick={() => setIsOpen((current) => !current)}
        className="mt-4 flex h-12 w-full items-center justify-between rounded-2xl border-[var(--border)] bg-[var(--card)] text-[var(--foreground)] hover:bg-[var(--accent)]"
        data-testid="notification-center-toggle-button"
      >
        <span className="flex items-center gap-2"><Bell className="h-4 w-4" />Notifications</span>
        <Badge className="border-0 bg-[var(--accent)] px-3 py-1 text-[var(--foreground)]" data-testid="notification-center-unread-badge">{unreadCount}</Badge>
      </Button>

      {isOpen && (
        <Card className="absolute left-0 right-0 top-[calc(100%+12px)] z-40 rounded-[28px] border-border/80 bg-[var(--card)] shadow-xl" data-testid="notification-center-panel">
          <CardContent className="max-h-[420px] space-y-3 overflow-y-auto p-5">
            {notifications.length === 0 ? (
              <p className="text-sm text-[var(--muted-foreground)]" data-testid="notification-center-empty-state">No notifications yet.</p>
            ) : (
              notifications.map((item) => (
                <div key={item.id} className="rounded-[22px] border border-[var(--border)] bg-[var(--accent)] p-4" data-testid={`notification-item-${item.id}`}>
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-[var(--foreground)]" data-testid={`notification-title-${item.id}`}>{item.title}</p>
                      <p className="mt-1 text-sm text-[var(--muted-foreground)]" data-testid={`notification-message-${item.id}`}>{item.message}</p>
                    </div>
                    <Badge className="border-0 bg-[var(--card)] px-3 py-1 text-[var(--foreground)]">{item.status}</Badge>
                  </div>
                  {item.status === "unread" && (
                    <Button type="button" onClick={() => markRead(item.id)} className="mt-3 h-10 rounded-2xl bg-[#243e36] hover:bg-[#1a2c26]" data-testid={`notification-read-button-${item.id}`}>
                      <CheckCircle2 className="mr-2 h-4 w-4" />Mark read
                    </Button>
                  )}
                </div>
              ))
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
