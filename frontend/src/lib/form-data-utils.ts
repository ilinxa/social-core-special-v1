/**
 * Utility for converting plain objects to FormData when file uploads are present.
 *
 * DRF ImageField with allow_null=True interprets empty string as "clear image".
 * Axios auto-detects FormData and sets multipart/form-data content type.
 */

/**
 * Returns FormData if any value is a File instance, otherwise returns the
 * original object for a standard JSON request.
 */
export function buildFormDataIfNeeded(
  data: Record<string, unknown>,
): FormData | Record<string, unknown> {
  const hasFile = Object.values(data).some((v) => v instanceof File);
  if (!hasFile) return data;

  const fd = new FormData();

  for (const [key, val] of Object.entries(data)) {
    if (val instanceof File) {
      fd.append(key, val);
    } else if (val === null || val === undefined) {
      // DRF ImageField: empty string = clear
      fd.append(key, "");
    } else if (typeof val === "object") {
      fd.append(key, JSON.stringify(val));
    } else {
      fd.append(key, String(val));
    }
  }

  return fd;
}
