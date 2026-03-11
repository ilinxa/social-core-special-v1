const SESSION_COOKIE_MAX_AGE = 604800; // 7 days (matches refresh token)

export function setSessionCookie(): void {
  if (typeof document !== "undefined") {
    document.cookie = `has_session=1; path=/; SameSite=Strict; max-age=${SESSION_COOKIE_MAX_AGE}`;
  }
}

export function clearSessionCookie(): void {
  if (typeof document !== "undefined") {
    document.cookie = "has_session=; path=/; SameSite=Strict; max-age=0";
  }
}
