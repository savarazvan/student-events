#!/usr/bin/env sh
# Run on the VPS before the first deploy:  sh deploy/server-check.sh
# Prints what the deployment needs to know; changes nothing.

echo "== Operating system"
. /etc/os-release 2>/dev/null && echo "$PRETTY_NAME" || uname -a

echo
echo "== CPU / RAM / disk"
nproc 2>/dev/null | sed 's/^/CPUs: /'
free -h 2>/dev/null | sed -n '1,2p'
df -h / | tail -1 | awk '{print "Disk /: " $4 " free of " $2}'

echo
echo "== Docker"
docker --version 2>/dev/null || echo "Docker: NOT installed"
docker compose version 2>/dev/null || echo "Docker Compose plugin: NOT installed"

echo
echo "== Who is using ports 80 / 443 (must be free for Caddy)"
if command -v ss >/dev/null 2>&1; then
  ss -ltnp 2>/dev/null | awk 'NR==1 || /:(80|443) /'
else
  netstat -ltnp 2>/dev/null | awk 'NR<=2 || /:(80|443) /'
fi
for svc in nginx apache2 httpd caddy; do
  systemctl is-active --quiet "$svc" 2>/dev/null && echo "Service running: $svc"
done

echo
echo "== Firewall"
command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | head -5 || echo "ufw not present"

echo
echo "== Public IP of this server"
curl -s -4 https://ifconfig.me 2>/dev/null || echo "(could not detect)"
echo
echo "== DNS for events.alexandrupaloti.com"
getent hosts events.alexandrupaloti.com 2>/dev/null || echo "Not resolving yet (add an A record to the IP above)"
