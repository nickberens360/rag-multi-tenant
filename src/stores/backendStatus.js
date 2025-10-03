import { atom, computed } from 'nanostores';

// Change initial values from optimistic (true) to unknown (null)
export const isBackendOnline = atom(null);
export const isBackendInitialized = atom(null);
export const isBackendBuilding = atom(null);
export const lastStatusCheck = atom(null);

// Add a computed status atom that derives a single status string from the individual states
export const backendStatus = computed([isBackendOnline, isBackendInitialized, isBackendBuilding],
  (online, initialized, building) => {
    if (online === null) return 'checking';
    if (!online) return 'offline';
    if (building) return 'building';
    if (initialized) return 'online';
    return 'initializing';
  }
);

// Function to update backend status
export function updateBackendStatus(status) {
  isBackendOnline.set(status.online);
  isBackendInitialized.set(status.initialized);
  isBackendBuilding.set(status.building);
  lastStatusCheck.set(Date.now());
}
