import { useEffect, useMemo, useState } from 'react';

import { listPublicOrganizations } from '../api/organizations';
import type { OrganizationResponse } from '../types';

// Organizations change rarely: share one request across all components.
let cache: Promise<OrganizationResponse[]> | null = null;

function loadOrganizations(): Promise<OrganizationResponse[]> {
  if (!cache) {
    cache = listPublicOrganizations().catch((err) => {
      cache = null;
      throw err;
    });
  }
  return cache;
}

export function invalidateOrganizations(): void {
  cache = null;
}

export function useOrganizations() {
  const [organizations, setOrganizations] = useState<OrganizationResponse[]>([]);

  useEffect(() => {
    let ignore = false;
    loadOrganizations()
      .then((orgs) => {
        if (!ignore) setOrganizations(orgs);
      })
      .catch(() => {
        // Names are cosmetic; the UI falls back gracefully.
      });
    return () => {
      ignore = true;
    };
  }, []);

  const nameById = useMemo(
    () => new Map(organizations.map((org) => [org.id, org.name])),
    [organizations],
  );

  return { organizations, nameById };
}
