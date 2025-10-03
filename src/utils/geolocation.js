// EEA countries (EU + Iceland, Liechtenstein, Norway)
const EEA_COUNTRIES = new Set([
  'AT', 'BE', 'BG', 'HR', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR', 'DE', 'GR', 'HU', 'IE', 'IT', 'LV',
  'LT', 'LU', 'MT', 'NL', 'PL', 'PT', 'RO', 'SK', 'SI', 'ES', 'SE', 'IS', 'LI', 'NO'
]);

class GeolocationService {
  constructor() {
    this.cacheExpiry = 24 * 60 * 60 * 1000; // 24 hours
    this.locationPromise = null;
  }

  async getUserLocation() {
    // Check localStorage cache first
    const cached = this.getCachedLocation();
    if (cached) {
      return cached;
    }

    // If a request is already in flight, return its promise
    if (this.locationPromise) {
      return this.locationPromise;
    }

    // Start a new request and store the promise
    this.locationPromise = (async () => {
      try {
        const location = await this.detectLocationWithFallback();
        this.cacheLocation(location);
        return location;
      } catch (error) {
        console.warn('Geolocation detection failed:', error);
        // Default to requiring consent if we can't determine location
        return { countryCode: 'UNKNOWN', isEEA: true, source: 'fallback' };
      } finally {
        // Clear the promise after it resolves to allow for future retries
        this.locationPromise = null;
      }
    })();

    return this.locationPromise;
  }

  async detectLocationWithFallback() {
    const services = [
      () => this.detectViaIpApi(),
      () => this.detectViaCloudflare(),
      () => this.detectViaTimezone()
    ];

    for (const service of services) {
      try {
        const result = await service();
        if (result && result.countryCode) {
          return result;
        }
      } catch (error) {
        console.warn('Geolocation service failed, trying next:', error);
        continue;
      }
    }

    throw new Error('All geolocation services failed');
  }

  async detectViaIpApi() {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 3000);

    try {
      const response = await fetch('https://ipapi.co/json/', {
        signal: controller.signal,
        headers: {
          'Accept': 'application/json'
        }
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const data = await response.json();
      if (data.error) throw new Error(data.reason || 'API error');

      return {
        countryCode: data.country_code,
        country: data.country_name,
        isEEA: EEA_COUNTRIES.has(data.country_code),
        source: 'ipapi.co'
      };
    } finally {
      clearTimeout(timeout);
    }
  }

  async detectViaCloudflare() {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 3000);

    try {
      const response = await fetch('https://cloudflare.com/cdn-cgi/trace', {
        signal: controller.signal
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const text = await response.text();
      const lines = text.split('\n');
      const locLine = lines.find(line => line.startsWith('loc='));

      if (!locLine) throw new Error('No location data');

      const countryCode = locLine.split('=', 2)[1]?.trim().toUpperCase();
      if (!countryCode || countryCode.length !== 2) {
        throw new Error('Malformed location data from Cloudflare');
      }

      return {
        countryCode: countryCode,
        isEEA: EEA_COUNTRIES.has(countryCode),
        source: 'cloudflare'
      };
    } finally {
      clearTimeout(timeout);
    }
  }

  async detectViaTimezone() {
    // Fallback: rough estimation based on timezone
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

    // Common European timezones that might indicate EEA location
    const europeanTimezones = [
      'Europe/', 'Atlantic/Reykjavik', 'Atlantic/Faroe'
    ];

    const isLikelyEurope = europeanTimezones.some(tz => timezone.startsWith(tz));

    return {
      countryCode: 'ESTIMATED',
      timezone: timezone,
      isEEA: isLikelyEurope,
      source: 'timezone-estimation'
    };
  }

  getCachedLocation() {
    try {
      const cached = localStorage.getItem('user-location');
      if (!cached) return null;

      const { data, timestamp } = JSON.parse(cached);

      // Check if cache is expired
      if (Date.now() - timestamp > this.cacheExpiry) {
        localStorage.removeItem('user-location');
        return null;
      }

      return data;
    } catch (error) {
      console.warn('Error reading location cache:', error);
      return null;
    }
  }

  cacheLocation(location) {
    try {
      const cacheData = {
        data: location,
        timestamp: Date.now()
      };
      localStorage.setItem('user-location', JSON.stringify(cacheData));
    } catch (error) {
      console.warn('Error caching location:', error);
    }
  }


  // Clear cache (useful for testing)
  clearCache() {
    localStorage.removeItem('user-location');
  }
}

// Export singleton instance
export const geolocationService = new GeolocationService();

// Export helper functions
export const isEEACountry = (countryCode) => EEA_COUNTRIES.has(countryCode);
export const EEA_COUNTRY_LIST = Array.from(EEA_COUNTRIES);
