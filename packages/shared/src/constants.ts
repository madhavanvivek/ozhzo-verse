export const APP_NAME = 'Ozhzo Verse';
export const APP_DESCRIPTION = 'The Digital Operating System for Homes';

export const DEFAULT_INVENTORY_CATEGORIES = [
  { name: 'Pantry', icon: 'cookie', sort_order: 1 },
  { name: 'Fridge', icon: 'refrigerator', sort_order: 2 },
  { name: 'Freezer', icon: 'snowflake', sort_order: 3 },
  { name: 'Cleaning', icon: 'sparkles', sort_order: 4 },
  { name: 'Medicine', icon: 'pill', sort_order: 5 },
  { name: 'Other', icon: 'package', sort_order: 6 }
] as const;

export const FREE_TIER_LIMITS = {
  MAX_HOMES: 1,
  MAX_MEMBERS_PER_HOME: 5,
  MAX_INVENTORY_ITEMS: 100
} as const;

export const INVITE_EXPIRATION_DAYS = 7;
export const ACCESS_TOKEN_EXPIRATION_MINUTES = 15;
export const REFRESH_TOKEN_EXPIRATION_DAYS = 30;

export const DATE_FORMATS = {
  DISPLAY_DATE: 'MMM d, yyyy',
  DISPLAY_DATETIME: 'MMM d, yyyy h:mm a',
  ISO_DATE: 'yyyy-MM-dd'
} as const;
