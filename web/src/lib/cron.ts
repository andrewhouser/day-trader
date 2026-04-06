/**
 * Convert a 5-field cron expression to a human-readable string.
 * Handles the patterns used in this project's task schedules.
 */

const DAY_NAMES: Record<string, string> = {
  "0": "Sun", "1": "Mon", "2": "Tue", "3": "Wed", "4": "Thu", "5": "Fri", "6": "Sat", "7": "Sun",
};

function describeDays(field: string): string {
  if (field === "*") return "";
  // Range like 1-5
  const range = field.match(/^(\d)-(\d)$/);
  if (range) {
    const from = DAY_NAMES[range[1]] ?? range[1];
    const to = DAY_NAMES[range[2]] ?? range[2];
    return `${from}–${to}`;
  }
  // Single day
  if (DAY_NAMES[field]) return DAY_NAMES[field];
  return field;
}

function describeHours(field: string): string {
  if (field === "*") return "";
  const range = field.match(/^(\d+)-(\d+)$/);
  if (range) {
    const from = parseInt(range[1]);
    const to = parseInt(range[2]);
    return `${fmtHour(from)}–${fmtHour(to)}`;
  }
  // Comma-separated like 8,12,16
  if (field.includes(",")) {
    return field.split(",").map((h) => fmtHour(parseInt(h))).join(", ");
  }
  return `at ${fmtHour(parseInt(field))}`;
}

function fmtHour(h: number): string {
  if (h === 0) return "12 AM";
  if (h < 12) return `${h} AM`;
  if (h === 12) return "12 PM";
  return `${h - 12} PM`;
}

function fmtTime(h: number, m: number): string {
  const minStr = m > 0 ? `:${m.toString().padStart(2, "0")}` : "";
  if (h === 0) return `12${minStr} AM`;
  if (h < 12) return `${h}${minStr} AM`;
  if (h === 12) return `12${minStr} PM`;
  return `${h - 12}${minStr} PM`;
}

export function cronToHuman(cron: string): string {
  const parts = cron.trim().split(/\s+/);
  if (parts.length !== 5) return cron;

  const [minute, hour, , , dow] = parts;
  const days = describeDays(dow);

  // Every N minutes: */3 9-16 * * 1-5
  const everyMin = minute.match(/^\*\/(\d+)$/);
  if (everyMin) {
    const n = everyMin[1];
    const hours = describeHours(hour);
    const dayStr = days ? `, ${days}` : "";
    return `Every ${n} min${hours ? `, ${hours}` : ""}${dayStr}`;
  }

  // Step with offset: 5/10 9-16 * * 1-5
  const stepMin = minute.match(/^(\d+)\/(\d+)$/);
  if (stepMin) {
    const n = stepMin[2];
    const hours = describeHours(hour);
    const dayStr = days ? `, ${days}` : "";
    return `Every ${n} min${hours ? `, ${hours}` : ""}${dayStr}`;
  }

  // Specific minutes with hour range: 0,30 9-16 * * 1-5
  if (minute.includes(",") && !hour.includes(",")) {
    const mins = minute.split(",");
    const interval = mins.length === 2 && mins[0] === "0" ? `${mins[1]}` : null;
    const hours = describeHours(hour);
    const dayStr = days ? `, ${days}` : "";
    if (interval) {
      return `Every ${interval} min${hours ? `, ${hours}` : ""}${dayStr}`;
    }
  }

  // Specific time: 0 7 * * 1-5
  if (/^\d+$/.test(minute) && /^[\d,]+$/.test(hour)) {
    const min = parseInt(minute);

    // Multiple hours: 0 8,12,16 * * 1-5
    if (hour.includes(",")) {
      const times = hour.split(",").map((h) => fmtTime(parseInt(h), min));
      const dayStr = days ? `, ${days}` : "";
      return times.join(", ") + dayStr;
    }

    // Single hour
    const hr = parseInt(hour);
    const dayStr = days ? `, ${days}` : "";
    return `${fmtTime(hr, min)}${dayStr}`;
  }

  return cron;
}
