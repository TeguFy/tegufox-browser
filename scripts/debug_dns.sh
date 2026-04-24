#!/usr/bin/env bash
# Debug fv.pro DNS resolution across ISP + global resolvers.
# Run: bash scripts/debug_dns.sh [domain]
# Default domain is fv.pro.

set -u
DOMAIN="${1:-fv.pro}"
echo "=== Resolving $DOMAIN across resolvers ==="
echo

# Viettel DNS servers (try common ones — your actual ISP may differ)
for resolver in 203.113.131.1 203.113.188.1 203.162.4.1 203.162.4.190 ; do
  printf "Viettel (%-16s): " "$resolver"
  ans=$(dig +short +time=3 +tries=1 @"$resolver" "$DOMAIN" 2>/dev/null | head -1)
  [ -z "$ans" ] && ans="(no answer / blocked)"
  echo "$ans"
done

# System default
printf "System default DNS : "
ans=$(dig +short +time=3 "$DOMAIN" 2>/dev/null | head -1)
[ -z "$ans" ] && ans="(no answer)"
echo "$ans"

echo
echo "=== Global DoH resolvers (what Tegufox uses with dns_strategy=doh) ==="
for pair in "cloudflare-dns.com" "dns.google/resolve" "dns.nextdns.io/dns-query" ; do
  base="${pair%%/*}"
  path="${pair#*/}"; [ "$path" = "$pair" ] && path="dns-query"
  printf "%-30s: " "$base"
  status=$(curl -s -H 'accept: application/dns-json' \
    "https://$base/$path?name=$DOMAIN&type=A" 2>/dev/null | \
    python3 -c "import sys,json; d=json.load(sys.stdin); a=[x.get('data') for x in d.get('Answer',[])]; print(','.join(a) or f'NXDOMAIN (status={d.get(\"Status\")})')" 2>/dev/null)
  [ -z "$status" ] && status="(request failed)"
  echo "$status"
done

echo
echo "=== If Viettel resolves but global doesn't: GEO-DNS. Use dns_strategy=os."
echo "=== If NOTHING resolves: domain may be dead, or you need a specific ISP DNS."
