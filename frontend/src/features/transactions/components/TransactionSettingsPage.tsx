"use client";

import { useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import {
  useTransactionTypes,
  useFormMappings,
} from "@/features/transactions/hooks/use-transaction-queries";
import {
  useCreateFormMapping,
  useDeleteFormMapping,
} from "@/features/transactions/hooks/use-transaction-mutations";
import { useTemplateList } from "@/features/forms/hooks/use-form-queries";
import { useBusiness } from "@/features/business/hooks/use-business-queries";
import { usePlatformAccount } from "@/features/platform/hooks/use-platform-queries";
import { updateBusinessApi } from "@/features/business/api/business-api";
import { updatePlatformSettingsApi } from "@/features/platform/api/platform-api";
import { TRANSACTION_CATEGORY_CONFIG } from "@/features/transactions/constants/transaction-statuses";
import { useHasPermission } from "@/hooks/use-has-permission";
import type { AccountType } from "@/types/rbac";
import type { TransactionTypeInfo, TransactionFormMapping } from "@/types/transactions";

interface TransactionSettingsPageProps {
  accountType: AccountType;
  accountId: string;
  slug?: string;
  maxMembers?: number;
}

// =============================================================================
// MEMBER REQUEST TOGGLE
// =============================================================================

function MemberRequestToggle({
  accountType,
  slug,
}: {
  accountType: AccountType;
  slug: string;
}) {
  const [toggling, setToggling] = useState(false);

  const businessQuery = useBusiness(accountType === "business" ? slug : "");
  const platformQuery = usePlatformAccount();

  const account = accountType === "business" ? businessQuery.data : platformQuery.data;
  const isOpen = account?.open_member_request ?? false;
  const accountLabel = accountType === "business" ? "business" : "platform";

  async function handleToggle(checked: boolean) {
    setToggling(true);
    try {
      if (accountType === "business") {
        await updateBusinessApi(slug, { open_member_request: checked });
        businessQuery.refetch();
      } else {
        await updatePlatformSettingsApi({ open_member_request: checked });
        platformQuery.refetch();
      }
      toast.success(
        checked
          ? `Member requests are now open for this ${accountLabel}.`
          : `Member requests are now closed for this ${accountLabel}.`,
      );
    } catch {
      toast.error("Failed to update member request setting.");
    } finally {
      setToggling(false);
    }
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Membership Requests</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <p className="text-sm font-medium">
              Accept membership requests
            </p>
            <p className="text-xs text-muted-foreground">
              When enabled, users can request to join this {accountLabel} from
              the public profile page.
            </p>
          </div>
          <Switch
            checked={isOpen}
            onCheckedChange={handleToggle}
            disabled={toggling}
            aria-label="Toggle membership requests"
          />
        </div>
      </CardContent>
    </Card>
  );
}

// =============================================================================
// TRANSACTION SETTINGS PAGE
// =============================================================================

export function TransactionSettingsPage({
  accountType,
  accountId,
  slug = "",
  maxMembers = 0,
}: TransactionSettingsPageProps) {
  const canConfigure = useHasPermission("can_configure_transactions", accountType, accountId);

  const [attachDialogOpen, setAttachDialogOpen] = useState(false);
  const [attachTransactionType, setAttachTransactionType] = useState("");
  const [selectedTemplateId, setSelectedTemplateId] = useState("");
  const [isRequired, setIsRequired] = useState(false);
  const [removeMappingId, setRemoveMappingId] = useState<string | null>(null);

  const { data: types, isLoading: typesLoading } = useTransactionTypes(accountType);
  const { data: mappings, isLoading: mappingsLoading } = useFormMappings(
    accountType,
    accountId,
  );
  const { data: templates } = useTemplateList(accountType, accountId);
  const createMapping = useCreateFormMapping(accountType, accountId);
  const deleteMapping = useDeleteFormMapping(accountType, accountId);

  if (!canConfigure) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold tracking-tight">Transaction Settings</h1>
        <Card>
          <CardContent className="py-8">
            <p className="text-center text-muted-foreground">
              You do not have permission to configure transaction settings.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const isLoading = typesLoading || mappingsLoading;

  // Active templates only
  const activeTemplates = templates?.results?.filter((t) => t.status === "active") ?? [];

  function openAttachDialog(transactionType: string) {
    setAttachTransactionType(transactionType);
    setSelectedTemplateId("");
    setIsRequired(false);
    setAttachDialogOpen(true);
  }

  function handleAttach() {
    if (!selectedTemplateId || !attachTransactionType) return;

    createMapping.mutate(
      {
        account_type: accountType,
        account_id: accountId,
        transaction_type: attachTransactionType,
        form_template_id: selectedTemplateId,
        is_required: isRequired,
      },
      {
        onSuccess: () => {
          setAttachDialogOpen(false);
        },
      },
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        {Array.from({ length: 3 }, (_, i) => (
          <Skeleton key={i} className="h-24 w-full" />
        ))}
      </div>
    );
  }

  const configurableTypes = types?.filter((t) => t.user_configurable) ?? [];

  // Group by category
  const grouped = configurableTypes.reduce<
    Record<string, TransactionTypeInfo[]>
  >((acc, type) => {
    const cat = type.category;
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(type);
    return acc;
  }, {});

  function getMappingForType(typeId: string): TransactionFormMapping | undefined {
    return mappings?.find((m) => m.transaction_type === typeId);
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">
          Transaction Settings
        </h1>
        <p className="text-sm text-muted-foreground">
          Configure forms required for each transaction type.
        </p>
      </div>

      {/* Member request toggle — only for orgs with max_members > 1 (or 0 = unlimited) */}
      {(maxMembers === 0 || maxMembers > 1) && slug && (
        <MemberRequestToggle accountType={accountType} slug={slug} />
      )}

      {Object.entries(grouped).map(([category, categoryTypes]) => (
        <div key={category} className="space-y-3">
          <h2 className="text-lg font-semibold">
            {TRANSACTION_CATEGORY_CONFIG[
              category as keyof typeof TRANSACTION_CATEGORY_CONFIG
            ]?.label ?? category}
          </h2>

          {categoryTypes.map((type) => {
            const mapping = getMappingForType(type.id);

            return (
              <Card key={type.id}>
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm">{type.name}</CardTitle>
                    <div className="flex items-center gap-2">
                      <Badge variant="secondary" className="text-xs capitalize">
                        {type.mode}
                      </Badge>
                      {type.requires_form && (
                        <Badge variant="outline" className="text-xs">
                          Form Required
                        </Badge>
                      )}
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  {mapping ? (
                    <div className="flex items-center justify-between">
                      <div className="space-y-1">
                        <p className="text-sm font-medium">
                          {mapping.form_template_name}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {mapping.is_required ? "Required" : "Optional"}
                        </p>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setRemoveMappingId(mapping.id)}
                        disabled={deleteMapping.isPending}
                      >
                        Remove
                      </Button>
                    </div>
                  ) : (
                    <div className="flex items-center justify-between">
                      <p className="text-sm text-muted-foreground">
                        No custom form configured.
                      </p>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => openAttachDialog(type.id)}
                      >
                        Attach Form
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      ))}

      {Object.keys(grouped).length === 0 && (
        <p className="py-8 text-center text-muted-foreground">
          No configurable transaction types available.
        </p>
      )}

      {/* Remove Mapping Confirmation Dialog */}
      <Dialog
        open={removeMappingId !== null}
        onOpenChange={(open) => { if (!open) setRemoveMappingId(null); }}
      >
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Remove Form Mapping</DialogTitle>
            <DialogDescription>
              This will detach the form from this transaction type. Users will no
              longer be required to fill out the form for this transaction.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRemoveMappingId(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                if (removeMappingId) {
                  deleteMapping.mutate(removeMappingId, {
                    onSuccess: () => setRemoveMappingId(null),
                  });
                }
              }}
              disabled={deleteMapping.isPending}
            >
              {deleteMapping.isPending ? "Removing..." : "Remove"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Attach Form Dialog */}
      <Dialog open={attachDialogOpen} onOpenChange={setAttachDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Attach Form</DialogTitle>
            <DialogDescription>
              Select a form template to attach to this transaction type.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {activeTemplates.length === 0 ? (
              <p className="py-4 text-center text-sm text-muted-foreground">
                No active form templates found. Create a form template first.
              </p>
            ) : (
              <div className="max-h-64 space-y-1 overflow-y-auto">
                {activeTemplates.map((template) => (
                  <button
                    key={template.id}
                    className={`flex w-full items-center gap-3 rounded-md border p-3 text-left transition-colors ${
                      selectedTemplateId === template.id
                        ? "border-primary bg-primary/5"
                        : "hover:bg-muted"
                    }`}
                    onClick={() => setSelectedTemplateId(template.id)}
                  >
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium truncate">
                        {template.name}
                      </p>
                      {template.description && (
                        <p className="text-xs text-muted-foreground truncate">
                          {template.description}
                        </p>
                      )}
                    </div>
                    <Badge variant="secondary" className="text-xs shrink-0">
                      v{template.version}
                    </Badge>
                  </button>
                ))}
              </div>
            )}

            {activeTemplates.length > 0 && (
              <div className="flex items-center gap-2">
                <Checkbox
                  id="is-required"
                  checked={isRequired}
                  onCheckedChange={(checked) =>
                    setIsRequired(checked === true)
                  }
                />
                <Label htmlFor="is-required" className="text-sm">
                  Form is required (must be filled to complete transaction)
                </Label>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setAttachDialogOpen(false)}
            >
              Cancel
            </Button>
            <Button
              onClick={handleAttach}
              disabled={
                !selectedTemplateId || createMapping.isPending
              }
            >
              {createMapping.isPending ? "Attaching..." : "Attach"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
