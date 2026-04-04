import { API_PORT, MOBILE_BREAKPOINT } from "../constants";

function tryParseUrl(value) {
  if (!value || typeof value !== "string") return null;
  try {
    return new URL(value);
  } catch {
    return null;
  }
}

function readInjectedApiBase() {
  const candidates = [
    window.APP_CONFIG?.backendBaseUrl,
    window.APP_CONFIG?.apiBase,
    window.__APP_CONFIG?.backendBaseUrl,
    window.__APP_CONFIG?.apiBase,
  ];

  for (const candidate of candidates) {
    if (typeof candidate === "string" && candidate.trim()) {
      return candidate.trim().replace(/\/$/, "");
    }
  }

  return "";
}

function resolveOriginCandidate() {
  const referrerUrl = tryParseUrl(document.referrer);
  if (referrerUrl && referrerUrl.hostname && referrerUrl.protocol !== "about:") {
    return referrerUrl;
  }

  const ancestorOrigin = window.location.ancestorOrigins?.[0];
  const ancestorUrl = tryParseUrl(ancestorOrigin);
  if (ancestorUrl && ancestorUrl.hostname) {
    return ancestorUrl;
  }

  return new URL(window.location.href);
}

export function readForcedClientMode() {
  const params = new URLSearchParams(window.location.search);
  const requested = (params.get("client") || params.get("mode") || "").trim().toLowerCase();
  return requested === "wechat" || requested === "weixin" ? "wechat" : "default";
}

export function isWeChatEnvironment() {
  const userAgent = navigator.userAgent.toLowerCase();
  return userAgent.includes("micromessenger") || window.__wxjs_environment === "miniprogram";
}

export function resolveClientMode() {
  const globalMode = (window.__APP_CLIENT_MODE || "").trim().toLowerCase();
  if (globalMode === "wechat" || globalMode === "weixin") return "wechat";

  const forcedMode = readForcedClientMode();
  if (forcedMode !== "default") return forcedMode;
  return isWeChatEnvironment() ? "wechat" : "default";
}

export function isMobileWidth(width = window.innerWidth) {
  return width <= MOBILE_BREAKPOINT;
}

export function resolveApiBase() {
  const injected = readInjectedApiBase();
  if (injected) return injected;

  // API is routed through nginx on the same origin (port 80/443).
  // No separate API_PORT needed; avoids firewall / security-group issues.
  return window.location.origin;
}
