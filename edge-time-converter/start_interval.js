(function () {
  // ── Shared timezone offset table ────────────────────────────────────────────
  const TZ_OFFSETS = {
    // North America
    NST: -3.5, NDT: -2.5,
    AST: -4,   ADT: -3,
    EST: -5,   EDT: -4,
    CST: -6,   CDT: -5,
    MST: -7,   MDT: -6,
    PST: -8,   PDT: -7,
    AKST: -9,  AKDT: -8,
    HST: -10,  HDT: -9,
    SST: -11,
    // Europe
    GMT: 0,    UTC: 0,
    WET: 0,    WEST: 1,
    CET: 1,    CEST: 2,
    EET: 2,    EEST: 3,
    MSK: 3,
    // Asia / Pacific
    IST: 5.5,
    PKT: 5,
    BST: 6,
    ICT: 7,
    WIB: 7,
    CST_CN: 8,
    HKT: 8,    SGT: 8,    AWST: 8,
    JST: 9,    KST: 9,    ACST: 9.5,
    AEST: 10,  AEDT: 11,
    NZST: 12,  NZDT: 13,
    // Middle East / Africa
    AST_AR: 3,
    EAT: 3,
    CAT: 2,
    WAT: 1,
    // South America
    ART: -3,   BRT: -3,   BRST: -2,
    PET: -5,   COT: -5,   ECT: -5,
    CLT: -4,   CLST: -3,
    VET: -4,
    BOT: -4,
  };

  // ── Shared helpers ───────────────────────────────────────────────────────────
  const TIME_RE = /\b(\d{1,2}):(\d{2})(AM|PM)\s+([A-Z]{2,5})\b/g;

  function toGMT(hours, minutes, ampm, tz) {
    let h = parseInt(hours, 10);
    const m = parseInt(minutes, 10);
    if (ampm === 'AM') {
      if (h === 12) h = 0;
    } else {
      if (h !== 12) h += 12;
    }
    const offset = TZ_OFFSETS[tz];
    if (offset === undefined) return null;
    let totalMinutes = h * 60 + m - offset * 60;
    totalMinutes = ((totalMinutes % 1440) + 1440) % 1440;
    const pad = n => String(n).padStart(2, '0');
    return `${pad(Math.floor(totalMinutes / 60))}:${pad(totalMinutes % 60)} GMT`;
  }

  function walkTextNodes(root, nodeTest, replacer) {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        const tag = node.parentElement?.tagName;
        if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'NOSCRIPT') {
          return NodeFilter.FILTER_REJECT;
        }
        return nodeTest(node.nodeValue)
          ? NodeFilter.FILTER_ACCEPT
          : NodeFilter.FILTER_SKIP;
      }
    });
    const nodes = [];
    let node;
    while ((node = walker.nextNode())) nodes.push(node);
    for (const textNode of nodes) {
      const original = textNode.nodeValue;
      const replaced = replacer(original);
      if (replaced !== original) {
        // Store the original only on first conversion; subsequent passes keep
        // the first-seen value so we can always restore to what the page had.
        if (!window.__gmtOriginals.has(textNode)) {
          window.__gmtOriginals.set(textNode, original);
        }
        textNode.nodeValue = replaced;
      }
    }
  }

  // ── General site: "10:28AM MDT" ─────────────────────────────────────────────
  function generalNodeTest(value) {
    TIME_RE.lastIndex = 0;
    return TIME_RE.test(value);
  }

  function generalReplacer(value) {
    TIME_RE.lastIndex = 0;
    return value.replace(TIME_RE, (match, hh, mm, ampm, tz) => {
      const gmt = toGMT(hh, mm, ampm, tz);
      return gmt ?? match;
    });
  }

  // ── LoggingNight.org: "06:26 AM" (no TZ code — derive from city/date) ───────
  // US state abbreviation → IANA timezone (most-populated zone for each state)
  const STATE_TZ = {
    AL: 'America/Chicago',    AK: 'America/Anchorage',
    AZ: 'America/Phoenix',    AR: 'America/Chicago',
    CA: 'America/Los_Angeles',CO: 'America/Denver',
    CT: 'America/New_York',   DE: 'America/New_York',
    FL: 'America/New_York',   GA: 'America/New_York',
    HI: 'Pacific/Honolulu',   ID: 'America/Denver',
    IL: 'America/Chicago',    IN: 'America/Indiana/Indianapolis',
    IA: 'America/Chicago',    KS: 'America/Chicago',
    KY: 'America/New_York',   LA: 'America/Chicago',
    ME: 'America/New_York',   MD: 'America/New_York',
    MA: 'America/New_York',   MI: 'America/Detroit',
    MN: 'America/Chicago',    MS: 'America/Chicago',
    MO: 'America/Chicago',    MT: 'America/Denver',
    NE: 'America/Chicago',    NV: 'America/Los_Angeles',
    NH: 'America/New_York',   NJ: 'America/New_York',
    NM: 'America/Denver',     NY: 'America/New_York',
    NC: 'America/New_York',   ND: 'America/Chicago',
    OH: 'America/New_York',   OK: 'America/Chicago',
    OR: 'America/Los_Angeles',PA: 'America/New_York',
    RI: 'America/New_York',   SC: 'America/New_York',
    SD: 'America/Chicago',    TN: 'America/Chicago',
    TX: 'America/Chicago',    UT: 'America/Denver',
    VT: 'America/New_York',   VA: 'America/New_York',
    WA: 'America/Los_Angeles',WV: 'America/New_York',
    WI: 'America/Chicago',    WY: 'America/Denver',
    DC: 'America/New_York',
  };

  // Returns the UTC offset in minutes for the given IANA timezone on the given
  // date (YYYY-MM-DD).  Positive = ahead of UTC.  Uses the browser's built-in
  // timezone database so DST is handled automatically.
  function getUTCOffsetMinutes(ianaTimezone, dateStr) {
    // Use noon UTC to stay clear of any DST transition hour.
    const utcNoon = new Date(`${dateStr}T12:00:00Z`);
    const parts = new Intl.DateTimeFormat('en-US', {
      timeZone: ianaTimezone,
      hour: 'numeric',
      minute: 'numeric',
      hourCycle: 'h23',
    }).formatToParts(utcNoon);
    const h = parseInt(parts.find(p => p.type === 'hour').value, 10);
    const m = parseInt(parts.find(p => p.type === 'minute').value, 10);
    // Offset from UTC noon
    let offset = h * 60 + m - 720;
    if (offset > 840)  offset -= 1440;
    if (offset < -840) offset += 1440;
    return offset;
  }

  // Match "06:26 AM" or "6:26 PM" but NOT strings already followed by a TZ code
  // (to avoid re-converting our own "HH:MM GMT" output — those lack AM/PM anyway).
  const LN_TIME_RE = /\b(\d{1,2}):(\d{2})\s+(AM|PM)\b/g;

  function lnNodeTest(value) {
    LN_TIME_RE.lastIndex = 0;
    return LN_TIME_RE.test(value);
  }

  function makeLNReplacer(offsetMinutes) {
    return function lnReplacer(value) {
      LN_TIME_RE.lastIndex = 0;
      return value.replace(LN_TIME_RE, (match, hh, mm, ampm) => {
        let h = parseInt(hh, 10);
        const m = parseInt(mm, 10);
        if (ampm === 'AM') {
          if (h === 12) h = 0;
        } else {
          if (h !== 12) h += 12;
        }
        // UTC = local − offset
        let totalMinutes = h * 60 + m - offsetMinutes;
        totalMinutes = ((totalMinutes % 1440) + 1440) % 1440;
        const pad = n => String(n).padStart(2, '0');
        return `${pad(Math.floor(totalMinutes / 60))}:${pad(totalMinutes % 60)} GMT`;
      });
    };
  }

  function getLoggingNightOffset() {
    const dateEl  = document.getElementById('out_date');
    const cityEl  = document.getElementById('out_city_name');
    if (!dateEl || !cityEl) return null;

    const dateStr = dateEl.textContent.trim();           // "2026-04-13"
    const cityStr = cityEl.textContent.trim();           // "VAN NUYS, CA"
    const stateAbbr = cityStr.split(',').pop().trim().toUpperCase(); // "CA"

    const ianaTimezone = STATE_TZ[stateAbbr];
    if (!ianaTimezone || !dateStr) return null;

    return getUTCOffsetMinutes(ianaTimezone, dateStr);
  }

  // ── Observer setup ───────────────────────────────────────────────────────────
  const isLoggingNight = /loggingnight\.org/.test(window.location.hostname);

  function buildConverters() {
    if (isLoggingNight) {
      const offsetMinutes = getLoggingNightOffset();
      if (offsetMinutes === null) return null; // metadata not in DOM yet
      return { nodeTest: lnNodeTest, replacer: makeLNReplacer(offsetMinutes) };
    }
    return { nodeTest: generalNodeTest, replacer: generalReplacer };
  }

  function convertAll(converters) {
    if (!converters) return;
    walkTextNodes(document.body, converters.nodeTest, converters.replacer);
  }

  if (window.__gmtObserver) {
    window.__gmtObserver.disconnect();
  }
  // Reset the originals map each time the extension is enabled.
  window.__gmtOriginals = new Map();

  // Initial pass — build converters now; on LoggingNight they may not be ready
  // yet if the page is still loading, so we fall back gracefully.
  let converters = buildConverters();
  convertAll(converters);

  const observerConfig = { childList: true, subtree: true, characterData: true };

  window.__gmtObserver = new MutationObserver((mutations) => {
    window.__gmtObserver.disconnect();

    // On LoggingNight, re-derive the offset on every mutation batch in case
    // #out_date / #out_city_name were updated by the page.
    if (isLoggingNight) {
      converters = buildConverters();
    }

    const targets = new Set();
    for (const mutation of mutations) {
      if (mutation.type === 'childList') {
        mutation.addedNodes.forEach(node => {
          if (node.nodeType === Node.ELEMENT_NODE) {
            targets.add(node);
          } else if (node.nodeType === Node.TEXT_NODE && node.parentElement) {
            targets.add(node.parentElement);
          }
        });
      } else if (mutation.type === 'characterData') {
        const node = mutation.target;
        // If the page rewrote a text node we own, update our stored original to
        // the page's new value before we re-convert it below.
        if (window.__gmtOriginals.has(node)) {
          window.__gmtOriginals.set(node, node.nodeValue);
        }
        if (node.parentElement) targets.add(node.parentElement);
      }
    }

    if (converters) {
      for (const target of targets) {
        if (document.body.contains(target)) {
          walkTextNodes(target, converters.nodeTest, converters.replacer);
        }
      }
    }

    window.__gmtObserver.observe(document.body, observerConfig);
  });

  window.__gmtObserver.observe(document.body, observerConfig);
})();
