export const queryKeys = {
  auth: {
    all: ["auth"] as const,
    sessions: () => [...queryKeys.auth.all, "sessions"] as const,
  },
  users: {
    all: ["users"] as const,
    me: () => [...queryKeys.users.all, "me"] as const,
    profile: () => [...queryKeys.users.all, "me", "profile"] as const,
    checkUsername: (username: string) =>
      [...queryKeys.users.all, "check-username", username] as const,
    byUsername: (username: string) =>
      [...queryKeys.users.all, "username", username] as const,
    memberships: () => [...queryKeys.users.all, "memberships"] as const,
    withBusinessPermission: (params?: Record<string, unknown>) =>
      [...queryKeys.users.all, "with-business-permission", params] as const,
  },
  business: {
    all: ["business"] as const,
    list: () => [...queryKeys.business.all, "list"] as const,
    my: () => [...queryKeys.business.all, "my"] as const,
    detail: (slug: string) =>
      [...queryKeys.business.all, "detail", slug] as const,
    roles: (slug: string) =>
      [...queryKeys.business.all, slug, "roles"] as const,
    members: (slug: string) =>
      [...queryKeys.business.all, slug, "members"] as const,
  },
  platform: {
    all: ["platform"] as const,
    account: () => [...queryKeys.platform.all, "account"] as const,
    roles: () => [...queryKeys.platform.all, "roles"] as const,
    members: () => [...queryKeys.platform.all, "members"] as const,
  },
  rbac: {
    all: ["rbac"] as const,
    permissions: () => [...queryKeys.rbac.all, "permissions"] as const,
  },
  members: {
    all: ["members"] as const,
    list: (accountType: string, slug: string, params?: Record<string, unknown>) =>
      [...queryKeys.members.all, "list", accountType, slug, params] as const,
    detail: (id: string) =>
      [...queryKeys.members.all, "detail", id] as const,
  },
  roles: {
    all: ["roles"] as const,
    list: (accountType: string, slug: string) =>
      [...queryKeys.roles.all, "list", accountType, slug] as const,
    detail: (id: string) =>
      [...queryKeys.roles.all, "detail", id] as const,
  },
  transactions: {
    all: ["transactions"] as const,
    list: (params?: Record<string, unknown>) =>
      [...queryKeys.transactions.all, "list", params] as const,
    detail: (id: string) =>
      [...queryKeys.transactions.all, "detail", id] as const,
    types: (contextType?: string) =>
      [...queryKeys.transactions.all, "types", contextType] as const,
    formMappings: (accountType: string, accountId: string) =>
      [...queryKeys.transactions.all, "form-mappings", accountType, accountId] as const,
    formResponse: (transactionId: string) =>
      [...queryKeys.transactions.all, "form-response", transactionId] as const,
    requiredForm: (transactionId: string) =>
      [...queryKeys.transactions.all, "required-form", transactionId] as const,
    businessCreationRequest: () =>
      [...queryKeys.transactions.all, "business-creation-request"] as const,
  },
  forms: {
    all: ["forms"] as const,
    library: () => [...queryKeys.forms.all, "library"] as const,
    templates: (accountType: string, accountId: string) =>
      [...queryKeys.forms.all, "templates", accountType, accountId] as const,
    detail: (id: string) => [...queryKeys.forms.all, "detail", id] as const,
    responses: (formId: string, params?: Record<string, unknown>) =>
      [...queryKeys.forms.all, "responses", formId, params] as const,
    responseDetail: (id: string) =>
      [...queryKeys.forms.all, "response-detail", id] as const,
    myResponses: () =>
      [...queryKeys.forms.all, "my-responses"] as const,
  },
  notifications: {
    all: ["notifications"] as const,
    preferences: () => [...queryKeys.notifications.all, "preferences"] as const,
    history: () => [...queryKeys.notifications.all, "history"] as const,
  },
  network: {
    all: ["network"] as const,
    following: (type?: string) =>
      [...queryKeys.network.all, "following", type] as const,
    connections: (status?: string) =>
      [...queryKeys.network.all, "connections", status] as const,
    stats: () => [...queryKeys.network.all, "stats"] as const,
    businessFollowers: (slug: string) =>
      [...queryKeys.network.all, "business-followers", slug] as const,
    businessConnections: (slug: string) =>
      [...queryKeys.network.all, "business-connections", slug] as const,
    businessStats: (slug: string) =>
      [...queryKeys.network.all, "business-stats", slug] as const,
  },
  explore: {
    all: ["explore"] as const,
    combined: (params: Record<string, unknown>) =>
      [...queryKeys.explore.all, "combined", params] as const,
    businesses: (params: Record<string, unknown>) =>
      [...queryKeys.explore.all, "businesses", params] as const,
    users: (params: Record<string, unknown>) =>
      [...queryKeys.explore.all, "users", params] as const,
    tags: (q?: string, category?: string) =>
      [...queryKeys.explore.all, "tags", q, category] as const,
    cities: (country: string) =>
      [...queryKeys.explore.all, "cities", country] as const,
  },
};
