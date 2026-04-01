// ===== Hash utility =====
async function hashPassword(password) {
  const encoder = new TextEncoder();
  const data = encoder.encode(password);
  const hashBuffer = await crypto.subtle.digest("SHA-256", data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
}

// ===== Check if URL matches any blocked site =====
function isBlocked(url, blockedSites) {
  try {
    const hostname = new URL(url).hostname.replace(/^www\./, "").toLowerCase();
    return blockedSites.some((site) => {
      return hostname === site || hostname.endsWith("." + site);
    });
  } catch {
    return false;
  }
}

// ===== Track temporarily unlocked tabs =====
// Map of tabId -> Set of unlocked domains
const unlockedTabs = new Map();

// ===== Intercept navigation =====
chrome.webNavigation.onBeforeNavigate.addListener(async (details) => {
  // Only care about main frame
  if (details.frameId !== 0) return;

  const { blockedSites, passwordHash } = await chrome.storage.local.get([
    "blockedSites",
    "passwordHash",
  ]);

  if (!passwordHash || !blockedSites || blockedSites.length === 0) return;

  const url = details.url;
  if (!isBlocked(url, blockedSites)) return;

  // Check if this tab has been unlocked for this domain
  const tabUnlocked = unlockedTabs.get(details.tabId);
  if (tabUnlocked) {
    const hostname = new URL(url).hostname.replace(/^www\./, "").toLowerCase();
    const matchedSite = blockedSites.find(
      (site) => hostname === site || hostname.endsWith("." + site)
    );
    if (matchedSite && tabUnlocked.has(matchedSite)) {
      return; // Already unlocked
    }
  }

  // Redirect to blocked page
  const blockedPageUrl = chrome.runtime.getURL(
    `blocked/blocked.html?url=${encodeURIComponent(url)}`
  );

  chrome.tabs.update(details.tabId, { url: blockedPageUrl });
});

// ===== Listen for unlock messages from blocked page =====
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "VERIFY_PASSWORD") {
    (async () => {
      const { passwordHash } = await chrome.storage.local.get("passwordHash");
      const inputHash = await hashPassword(message.password);

      if (inputHash === passwordHash) {
        // Unlock this tab for the requested domain
        const tabId = sender.tab.id;
        if (!unlockedTabs.has(tabId)) {
          unlockedTabs.set(tabId, new Set());
        }

        try {
          const hostname = new URL(message.url).hostname
            .replace(/^www\./, "")
            .toLowerCase();
          const { blockedSites } = await chrome.storage.local.get(
            "blockedSites"
          );
          const matchedSite = (blockedSites || []).find(
            (site) => hostname === site || hostname.endsWith("." + site)
          );
          if (matchedSite) {
            unlockedTabs.get(tabId).add(matchedSite);
          }
        } catch {}

        sendResponse({ success: true });
      } else {
        sendResponse({ success: false });
      }
    })();
    return true; // Keep message channel open for async response
  }
});

// ===== Clean up when tab is closed =====
chrome.tabs.onRemoved.addListener((tabId) => {
  unlockedTabs.delete(tabId);
});

// ===== Clean up when tab navigates to a new unrelated page =====
chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
  if (changeInfo.url) {
    const tabUnlocked = unlockedTabs.get(tabId);
    if (tabUnlocked) {
      try {
        const hostname = new URL(changeInfo.url).hostname
          .replace(/^www\./, "")
          .toLowerCase();
        // If new URL doesn't match any unlocked domain, clear unlock state
        let stillRelevant = false;
        for (const domain of tabUnlocked) {
          if (hostname === domain || hostname.endsWith("." + domain)) {
            stillRelevant = true;
            break;
          }
        }
        if (!stillRelevant) {
          unlockedTabs.delete(tabId);
        }
      } catch {}
    }
  }
});
