/**
 * Governance step-up authentication API functions.
 *
 * Uses the standard apiClient (not governance client) since these
 * endpoints issue governance tokens — they require standard auth,
 * not governance auth.
 *
 * Endpoints:
 *   POST /api/v1/auth/governance/authenticate/ — password step-up
 *   POST /api/v1/auth/governance/otp/send/     — send OTP code
 *   POST /api/v1/auth/governance/otp/verify/   — verify OTP code
 */

import { apiClient } from "@/lib/api-client";
import { setGovernanceToken } from "@/lib/governance-token";

export interface GovernanceTokenResponse {
  access: string;
  expires_in: number;
}

export interface GovernanceOtpSendResponse {
  message: string;
}

export async function governancePasswordAuthApi(
  password: string,
): Promise<GovernanceTokenResponse> {
  const response = await apiClient.post<GovernanceTokenResponse>(
    "/auth/governance/authenticate/",
    { password },
  );
  setGovernanceToken(response.data.access, response.data.expires_in);
  return response.data;
}

export async function governanceOtpSendApi(): Promise<GovernanceOtpSendResponse> {
  const response = await apiClient.post<GovernanceOtpSendResponse>(
    "/auth/governance/otp/send/",
  );
  return response.data;
}

export async function governanceOtpVerifyApi(
  code: string,
): Promise<GovernanceTokenResponse> {
  const response = await apiClient.post<GovernanceTokenResponse>(
    "/auth/governance/otp/verify/",
    { code },
  );
  setGovernanceToken(response.data.access, response.data.expires_in);
  return response.data;
}
