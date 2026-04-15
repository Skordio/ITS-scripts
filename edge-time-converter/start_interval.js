(function () {
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

    const gmtH = Math.floor(totalMinutes / 60);
    const gmtM = totalMinutes % 60;
    const pad = n => String(n).padStart(2, '0');
    return `${pad(gmtH)}:${pad(gmtM)} GMT`;
  }

  function walkTextNodes(root) {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        const tag = node.parentElement?.tagName;
        if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'NOSCRIPT') {
          return NodeFilter.FILTER_REJECT;
        }
        TIME_RE.lastIndex = 0;
        return TIME_RE.test(node.nodeValue)
          ? NodeFilter.FILTER_ACCEPT
          : NodeFilter.FILTER_SKIP;
      }
    });

    const nodes = [];
    let node;
    while ((node = walker.nextNode())) nodes.push(node);

    for (const textNode of nodes) {
      TIME_RE.lastIndex = 0;
      const original = textNode.nodeValue;
      const replaced = original.replace(TIME_RE, (match, hh, mm, ampm, tz) => {
        const gmt = toGMT(hh, mm, ampm, tz);
        return gmt ?? match;
      });
      if (replaced !== original) {
        textNode.nodeValue = replaced;
      }
    }
  }

  // Stop any previously running observer before starting a new one.
  if (window.__gmtObserver) {
    window.__gmtObserver.disconnect();
  }

  // Initial pass over the full page.
  walkTextNodes(document.body);

  const observerConfig = { childList: true, subtree: true, characterData: true };

  window.__gmtObserver = new MutationObserver((mutations) => {
    // Disconnect before mutating to prevent our own changes from re-triggering.
    window.__gmtObserver.disconnect();

    // Collect the minimal set of roots to re-walk.
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
      } else if (mutation.type === 'characterData' && mutation.target.parentElement) {
        targets.add(mutation.target.parentElement);
      }
    }

    for (const target of targets) {
      if (document.body.contains(target)) {
        walkTextNodes(target);
      }
    }

    window.__gmtObserver.observe(document.body, observerConfig);
  });

  window.__gmtObserver.observe(document.body, observerConfig);
})();
