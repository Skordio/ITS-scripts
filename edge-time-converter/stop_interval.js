if (window.__gmtObserver) {
  window.__gmtObserver.disconnect();
  window.__gmtObserver = null;
}
if (window.__gmtOriginals) {
  for (const [textNode, original] of window.__gmtOriginals) {
    textNode.nodeValue = original;
  }
  window.__gmtOriginals = null;
}
