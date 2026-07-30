const BYTE_UNITS = ['byte', 'kilobyte', 'megabyte', 'gigabyte', 'terabyte'] as const;

type ByteUnit = (typeof BYTE_UNITS)[number];

const fileSizeFormatterCache = new Map<ByteUnit, Intl.NumberFormat>();

function getFileSizeFormatter(unit: ByteUnit): Intl.NumberFormat {
  let formatter = fileSizeFormatterCache.get(unit);
  if (!formatter) {
    formatter = new Intl.NumberFormat(undefined, {
      style: 'unit',
      unit,
      unitDisplay: 'narrow',
      maximumFractionDigits: unit === 'byte' ? 0 : 1,
    });
    fileSizeFormatterCache.set(unit, formatter);
  }
  return formatter;
}

/** Format a byte count using Intl unit formatting (B, KB, MB, …). */
export function formatFileSize(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) {
    return getFileSizeFormatter('byte').format(0);
  }

  let value = bytes;
  let unitIndex = 0;

  while (value >= 1024 && unitIndex < BYTE_UNITS.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }

  return getFileSizeFormatter(BYTE_UNITS[unitIndex]).format(value);
}

const RELATIVE_TIME_INTERVALS: {
  limit: number;
  divisor: number;
  unit: Intl.RelativeTimeFormatUnit;
}[] = [
  { limit: 60, divisor: 1, unit: 'second' },
  { limit: 3600, divisor: 60, unit: 'minute' },
  { limit: 86400, divisor: 3600, unit: 'hour' },
  { limit: 604800, divisor: 86400, unit: 'day' },
  { limit: 2629800, divisor: 604800, unit: 'week' },
  { limit: 31557600, divisor: 2629800, unit: 'month' },
  { limit: Number.POSITIVE_INFINITY, divisor: 31557600, unit: 'year' },
];

let relativeTimeFormatter: Intl.RelativeTimeFormat | undefined;

function getRelativeTimeFormatter(): Intl.RelativeTimeFormat {
  if (!relativeTimeFormatter) {
    relativeTimeFormatter = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' });
  }
  return relativeTimeFormatter;
}

/** Format an ISO string or Date as a relative time label (e.g. "2 hours ago"). */
export function formatRelativeTime(
  isoOrDate: string | Date,
  now: Date = new Date()
): string {
  const date = typeof isoOrDate === 'string' ? new Date(isoOrDate) : isoOrDate;
  const diffSeconds = Math.round((date.getTime() - now.getTime()) / 1000);
  const absSeconds = Math.abs(diffSeconds);

  for (const { limit, divisor, unit } of RELATIVE_TIME_INTERVALS) {
    if (absSeconds < limit) {
      return getRelativeTimeFormatter().format(Math.round(diffSeconds / divisor), unit);
    }
  }

  return getRelativeTimeFormatter().format(
    Math.round(diffSeconds / 31557600),
    'year'
  );
}
