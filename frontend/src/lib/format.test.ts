import { describe, expect, it, vi, afterEach } from 'vitest';
import { formatFileSize, formatRelativeTime } from './format';

describe('formatFileSize', () => {
  it('formats zero bytes', () => {
    expect(formatFileSize(0)).toMatch(/0\s*B/i);
  });

  it('formats negative and non-finite values as zero', () => {
    expect(formatFileSize(-100)).toMatch(/0\s*B/i);
    expect(formatFileSize(Number.NaN)).toMatch(/0\s*B/i);
    expect(formatFileSize(Number.POSITIVE_INFINITY)).toMatch(/0\s*B/i);
  });

  it('formats bytes without decimals', () => {
    expect(formatFileSize(512)).toMatch(/512\s*B/i);
  });

  it('formats kilobytes', () => {
    expect(formatFileSize(1024)).toMatch(/1(\.0)?\s*KB/i);
  });

  it('formats megabytes', () => {
    expect(formatFileSize(1024 * 1024)).toMatch(/1(\.0)?\s*MB/i);
  });

  it('formats gigabytes', () => {
    expect(formatFileSize(1024 * 1024 * 1024)).toMatch(/1(\.0)?\s*GB/i);
  });
});

describe('formatRelativeTime', () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it('formats seconds in the past', () => {
    const now = new Date('2026-07-30T12:00:00.000Z');
    const past = new Date('2026-07-30T11:59:30.000Z');
    expect(formatRelativeTime(past, now)).toMatch(/30 seconds ago|in 30 seconds/i);
  });

  it('formats minutes in the past', () => {
    const now = new Date('2026-07-30T12:00:00.000Z');
    const past = new Date('2026-07-30T11:45:00.000Z');
    expect(formatRelativeTime(past, now)).toMatch(/15 minutes ago|in 15 minutes/i);
  });

  it('formats hours in the future', () => {
    const now = new Date('2026-07-30T12:00:00.000Z');
    const future = new Date('2026-07-30T14:00:00.000Z');
    expect(formatRelativeTime(future, now)).toMatch(/in 2 hours|2 hours from now/i);
  });

  it('accepts ISO strings', () => {
    const now = new Date('2026-07-30T12:00:00.000Z');
    expect(formatRelativeTime('2026-07-30T11:00:00.000Z', now)).toMatch(
      /1 hour ago|in 1 hour/i
    );
  });

  it('formats days in the past', () => {
    const now = new Date('2026-07-30T12:00:00.000Z');
    const past = new Date('2026-07-28T12:00:00.000Z');
    expect(formatRelativeTime(past, now)).toMatch(/2 days ago|in 2 days/i);
  });
});
