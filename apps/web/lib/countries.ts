export interface CountryInfo {
  name: string;
  iso2: string;
  iso3: string;
  currency: string;
  currencySymbol: string;
  currencyName: string;
  region: string;
  defaultTaxPct: number;
  paymentGateway: 'STRIPE' | 'RAZORPAY';
}

export interface CurrencyInfo {
  code: string;
  name: string;
  symbol: string;
}

export const CURRENCIES: CurrencyInfo[] = [
  { code: 'INR', name: 'Indian Rupee', symbol: '₹' },
  { code: 'AED', name: 'UAE Dirham', symbol: 'AED' },
  { code: 'SAR', name: 'Saudi Riyal', symbol: 'SAR' },
  { code: 'USD', name: 'US Dollar', symbol: '$' },
  { code: 'GBP', name: 'British Pound', symbol: '£' },
  { code: 'EUR', name: 'Euro', symbol: '€' },
  { code: 'SGD', name: 'Singapore Dollar', symbol: 'S$' },
  { code: 'AUD', name: 'Australian Dollar', symbol: 'A$' },
  { code: 'CAD', name: 'Canadian Dollar', symbol: 'C$' },
  { code: 'JPY', name: 'Japanese Yen', symbol: '¥' },
  { code: 'QAR', name: 'Qatari Riyal', symbol: 'QAR' },
  { code: 'KWD', name: 'Kuwaiti Dinar', symbol: 'KWD' },
  { code: 'OMR', name: 'Omani Rial', symbol: 'OMR' },
  { code: 'BHD', name: 'Bahraini Dinar', symbol: 'BHD' },
  { code: 'NZD', name: 'New Zealand Dollar', symbol: 'NZ$' },
  { code: 'CHF', name: 'Swiss Franc', symbol: 'CHF' },
  { code: 'MYR', name: 'Malaysian Ringgit', symbol: 'RM' },
  { code: 'ZAR', name: 'South African Rand', symbol: 'R' },
  { code: 'BRL', name: 'Brazilian Real', symbol: 'R$' },
  { code: 'MXN', name: 'Mexican Peso', symbol: 'Mex$' },
];

export function getCurrencyInfo(code: string): CurrencyInfo {
  if (!code) return { code: 'USD', name: 'US Dollar', symbol: '$' };
  const found = CURRENCIES.find((c) => c.code.toUpperCase() === code.trim().toUpperCase());
  if (found) return found;
  return { code: code.toUpperCase(), name: code.toUpperCase(), symbol: code.toUpperCase() };
}

export function getCurrencySymbol(code: string): string {
  return getCurrencyInfo(code).symbol;
}

export const COUNTRIES: CountryInfo[] = [
  { name: 'India', iso2: 'IN', iso3: 'IND', currency: 'INR', currencySymbol: '₹', currencyName: 'Indian Rupee', region: 'South Asia', defaultTaxPct: 18.0, paymentGateway: 'RAZORPAY' },
  { name: 'United Arab Emirates', iso2: 'AE', iso3: 'ARE', currency: 'AED', currencySymbol: 'AED', currencyName: 'UAE Dirham', region: 'Middle East', defaultTaxPct: 5.0, paymentGateway: 'STRIPE' },
  { name: 'Saudi Arabia', iso2: 'SA', iso3: 'SAU', currency: 'SAR', currencySymbol: 'SAR', currencyName: 'Saudi Riyal', region: 'Middle East', defaultTaxPct: 15.0, paymentGateway: 'STRIPE' },
  { name: 'United Kingdom', iso2: 'GB', iso3: 'GBR', currency: 'GBP', currencySymbol: '£', currencyName: 'British Pound', region: 'Europe', defaultTaxPct: 20.0, paymentGateway: 'STRIPE' },
  { name: 'United States', iso2: 'US', iso3: 'USA', currency: 'USD', currencySymbol: '$', currencyName: 'US Dollar', region: 'North America', defaultTaxPct: 0.0, paymentGateway: 'STRIPE' },
  { name: 'Singapore', iso2: 'SG', iso3: 'SGP', currency: 'SGD', currencySymbol: 'S$', currencyName: 'Singapore Dollar', region: 'Southeast Asia', defaultTaxPct: 9.0, paymentGateway: 'STRIPE' },
  { name: 'Australia', iso2: 'AU', iso3: 'AUS', currency: 'AUD', currencySymbol: 'A$', currencyName: 'Australian Dollar', region: 'Oceania', defaultTaxPct: 10.0, paymentGateway: 'STRIPE' },
  { name: 'Canada', iso2: 'CA', iso3: 'CAN', currency: 'CAD', currencySymbol: 'C$', currencyName: 'Canadian Dollar', region: 'North America', defaultTaxPct: 13.0, paymentGateway: 'STRIPE' },
  { name: 'Germany', iso2: 'DE', iso3: 'DEU', currency: 'EUR', currencySymbol: '€', currencyName: 'Euro', region: 'Europe', defaultTaxPct: 19.0, paymentGateway: 'STRIPE' },
  { name: 'France', iso2: 'FR', iso3: 'FRA', currency: 'EUR', currencySymbol: '€', currencyName: 'Euro', region: 'Europe', defaultTaxPct: 20.0, paymentGateway: 'STRIPE' },
  { name: 'Japan', iso2: 'JP', iso3: 'JPN', currency: 'JPY', currencySymbol: '¥', currencyName: 'Japanese Yen', region: 'East Asia', defaultTaxPct: 10.0, paymentGateway: 'STRIPE' },
  { name: 'Qatar', iso2: 'QA', iso3: 'QAT', currency: 'QAR', currencySymbol: 'QAR', currencyName: 'Qatari Riyal', region: 'Middle East', defaultTaxPct: 0.0, paymentGateway: 'STRIPE' },
  { name: 'Kuwait', iso2: 'KW', iso3: 'KWT', currency: 'KWD', currencySymbol: 'KWD', currencyName: 'Kuwaiti Dinar', region: 'Middle East', defaultTaxPct: 0.0, paymentGateway: 'STRIPE' },
  { name: 'Oman', iso2: 'OM', iso3: 'OMN', currency: 'OMR', currencySymbol: 'OMR', currencyName: 'Omani Rial', region: 'Middle East', defaultTaxPct: 5.0, paymentGateway: 'STRIPE' },
  { name: 'Bahrain', iso2: 'BH', iso3: 'BHR', currency: 'BHD', currencySymbol: 'BHD', currencyName: 'Bahraini Dinar', region: 'Middle East', defaultTaxPct: 10.0, paymentGateway: 'STRIPE' },
  { name: 'New Zealand', iso2: 'NZ', iso3: 'NZL', currency: 'NZD', currencySymbol: 'NZ$', currencyName: 'New Zealand Dollar', region: 'Oceania', defaultTaxPct: 15.0, paymentGateway: 'STRIPE' },
  { name: 'Switzerland', iso2: 'CH', iso3: 'CHE', currency: 'CHF', currencySymbol: 'CHF', currencyName: 'Swiss Franc', region: 'Europe', defaultTaxPct: 8.1, paymentGateway: 'STRIPE' },
  { name: 'Malaysia', iso2: 'MY', iso3: 'MYS', currency: 'MYR', currencySymbol: 'RM', currencyName: 'Malaysian Ringgit', region: 'Southeast Asia', defaultTaxPct: 8.0, paymentGateway: 'STRIPE' },
  { name: 'South Africa', iso2: 'ZA', iso3: 'ZAF', currency: 'ZAR', currencySymbol: 'R', currencyName: 'South African Rand', region: 'Africa', defaultTaxPct: 15.0, paymentGateway: 'STRIPE' },
  { name: 'Brazil', iso2: 'BR', iso3: 'BRA', currency: 'BRL', currencySymbol: 'R$', currencyName: 'Brazilian Real', region: 'Latin America', defaultTaxPct: 17.0, paymentGateway: 'STRIPE' },
  { name: 'Mexico', iso2: 'MX', iso3: 'MEX', currency: 'MXN', currencySymbol: 'Mex$', currencyName: 'Mexican Peso', region: 'Latin America', defaultTaxPct: 16.0, paymentGateway: 'STRIPE' },
  { name: 'Global / International', iso2: 'GLOBAL', iso3: 'GLB', currency: 'USD', currencySymbol: '$', currencyName: 'US Dollar', region: 'Global', defaultTaxPct: 0.0, paymentGateway: 'STRIPE' }
];

export function findCountry(query: string): CountryInfo | undefined {
  if (!query) return undefined;
  const q = query.trim().toUpperCase();
  return COUNTRIES.find(
    (c) =>
      c.iso2 === q ||
      c.iso3 === q ||
      c.name.toUpperCase() === q ||
      c.name.toUpperCase().includes(q) ||
      c.currency === q
  );
}

export function searchCountries(query: string): CountryInfo[] {
  if (!query) return COUNTRIES;
  const q = query.trim().toUpperCase();
  return COUNTRIES.filter(
    (c) =>
      c.name.toUpperCase().includes(q) ||
      c.iso2.includes(q) ||
      c.iso3.includes(q) ||
      c.currency.includes(q) ||
      c.region.toUpperCase().includes(q)
  );
}
