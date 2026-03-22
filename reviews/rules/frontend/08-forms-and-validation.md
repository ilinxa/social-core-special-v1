# 08 — Forms & Validation Rules

Pass/fail criteria for each checklist item. Apply these when auditing the codebase.

---

## 8.1 Form Library Consistency

| ID | Rule | Verdict |
|----|------|---------|
| 8.1.1 | FAIL if any form does not use useForm({ resolver: zodResolver(schema) }) from react-hook-form | PASS/FAIL |
| 8.1.2 | FAIL if any form field values are managed via useState instead of react-hook-form | PASS/FAIL |
| 8.1.3 | WARN if a form mixes register (uncontrolled) and Controller (controlled) for fields that could use a single approach | PASS/WARN |
| 8.1.4 | WARN if useForm is missing defaultValues or mode configuration | PASS/WARN |
| 8.1.5 | FAIL if isDirty, isSubmitting, isValid, or errors are derived from separate useState instead of useForm return | PASS/FAIL |
| 8.1.6 | FAIL if Formik, custom form hooks, or other form libraries exist alongside react-hook-form | PASS/FAIL |

## 8.2 Zod Validation Schemas

| ID | Rule | Verdict |
|----|------|---------|
| 8.2.1 | FAIL if shared schemas (email, password, name) are not in lib/validations/ or feature-specific files | PASS/FAIL |
| 8.2.2 | WARN if Zod schema constraints (min/max length, patterns, required) do not match backend serializer constraints | PASS/WARN |
| 8.2.3 | FAIL if complex validation (password confirm, date ranges, conditional required) does not use .refine() or .superRefine() | PASS/FAIL |
| 8.2.4 | FAIL if form data types are manually defined instead of using z.infer<typeof schema> | PASS/FAIL |
| 8.2.5 | WARN if create and edit forms duplicate validation rules instead of sharing a base schema | PASS/WARN |
| 8.2.6 | FAIL if validation logic exists in onSubmit handlers or onChange callbacks instead of Zod schemas | PASS/FAIL |
| 8.2.7 | WARN if Zod error messages are technical (e.g., "String must have minimum length of 3") instead of user-friendly | PASS/WARN |

## 8.3 Field Components

| ID | Rule | Verdict |
|----|------|---------|
| 8.3.1 | FAIL if no FormField wrapper component exists providing label-input-error layout for text inputs | PASS/FAIL |
| 8.3.2 | FAIL if FormTextarea does not follow the same label-input-error layout as FormField | PASS/FAIL |
| 8.3.3 | WARN if PasswordInput does not include a show/hide toggle | PASS/WARN |
| 8.3.4 | WARN if PasswordInput does not include a password strength indicator where appropriate | PASS/WARN |
| 8.3.5 | FAIL if FormTagInput does not handle array-type inputs with add/remove/chip rendering | PASS/FAIL |
| 8.3.6 | FAIL if ComboboxField does not provide searchable filtering for large option sets | PASS/FAIL |
| 8.3.7 | WARN if ImageUpload does not show a preview of the selected file before submission | PASS/WARN |
| 8.3.8 | FAIL if field components do not integrate with react-hook-form via register or Controller | PASS/FAIL |

## 8.4 Error Display

| ID | Rule | Verdict |
|----|------|---------|
| 8.4.1 | FAIL if validation errors are not displayed below their corresponding field | PASS/FAIL |
| 8.4.2 | FAIL if server validation errors are not mapped to specific fields via handleApiError + setError | PASS/FAIL |
| 8.4.3 | WARN if root-level (non-field) errors do not display at the top of the form | PASS/WARN |
| 8.4.4 | WARN if rate limiting (429) does not show a countdown message | PASS/WARN |
| 8.4.5 | PASS if field errors clear when the user starts editing the errored field (revalidation mode) | PASS/FAIL |
| 8.4.6 | WARN if error messages are not linked to inputs via aria-describedby | PASS/WARN |
| 8.4.7 | WARN if multiple errors per field show all errors instead of the most relevant one | PASS/WARN |

## 8.5 Dynamic Form Builder

| ID | Rule | Verdict |
|----|------|---------|
| 8.5.1 | FAIL if FormBuilder does not render fields from a template schema definition | PASS/FAIL |
| 8.5.2 | FAIL if FieldRenderer does not handle all supported field types (text, number, select, checkbox, radio, textarea, file, date) | PASS/FAIL |
| 8.5.3 | WARN if FieldConfigPanel does not allow setting label, placeholder, required, validation, default value, and help text | PASS/WARN |
| 8.5.4 | FAIL if field validation does not run per-field-type (length for text, range for number, options for select) | PASS/FAIL |
| 8.5.5 | WARN if drag-and-drop reordering of fields is not implemented | PASS/WARN |
| 8.5.6 | WARN if preview mode is not available to show the form as end users would see it | PASS/WARN |
| 8.5.7 | FAIL if form templates are not versioned, allowing existing responses to reference their submission version | PASS/FAIL |

## 8.6 Form Submission

| ID | Rule | Verdict |
|----|------|---------|
| 8.6.1 | FAIL if form onSubmit does not delegate to a TanStack Query mutation hook | PASS/FAIL |
| 8.6.2 | FAIL if the submit button is not disabled during isSubmitting or mutation.isPending | PASS/FAIL |
| 8.6.3 | WARN if successful submission does not show a toast notification or navigate to the appropriate page | PASS/WARN |
| 8.6.4 | FAIL if mutation errors are not caught and displayed via onError callback or handleApiError | PASS/FAIL |
| 8.6.5 | FAIL if double submission is possible (submit button not disabled during pending state) | PASS/FAIL |
| 8.6.6 | WARN if create forms do not reset after successful submission where appropriate | PASS/WARN |
| 8.6.7 | INFO if optimistic updates are not used for inline edits (acceptable if standard invalidation is used) | PASS/INFO |

## 8.7 File Upload

| ID | Rule | Verdict |
|----|------|---------|
| 8.7.1 | FAIL if no ImageUpload component exists for avatar and cover images | PASS/FAIL |
| 8.7.2 | WARN if file type validation does not run client-side before upload (accept attribute + Zod) | PASS/WARN |
| 8.7.3 | WARN if file size validation does not run client-side before upload | PASS/WARN |
| 8.7.4 | WARN if no preview is shown for selected files before submission | PASS/WARN |
| 8.7.5 | INFO if upload progress is not indicated for large files | PASS/INFO |
| 8.7.6 | WARN if uploaded files cannot be removed or replaced by the user | PASS/WARN |

## 8.8 Complex Form Patterns

| ID | Rule | Verdict |
|----|------|---------|
| 8.8.1 | INFO if multi-step form state is not maintained across steps (acceptable if no wizard-pattern forms exist) | PASS/INFO |
| 8.8.2 | WARN if conditional fields do not show/hide based on other field values where applicable | PASS/WARN |
| 8.8.3 | INFO if useFieldArray is not used for repeated field groups (acceptable if no dynamic lists exist) | PASS/INFO |
| 8.8.4 | FAIL if cross-field validation (password confirm, date ranges) does not use Zod .refine() | PASS/FAIL |
| 8.8.5 | INFO if nested object forms are not structured as nested objects in the schema (acceptable if no nested forms exist) | PASS/INFO |
| 8.8.6 | WARN if unsaved changes are not detected and the user is not warned before navigating away | PASS/WARN |

## 8.9 Form Accessibility

| ID | Rule | Verdict |
|----|------|---------|
| 8.9.1 | FAIL if inputs are not associated with labels via htmlFor/id | PASS/FAIL |
| 8.9.2 | WARN if required fields do not have a visual indicator (asterisk) and aria-required="true" | PASS/WARN |
| 8.9.3 | WARN if error messages are not linked to fields via aria-describedby | PASS/WARN |
| 8.9.4 | WARN if focus does not move to the first error field on submission failure | PASS/WARN |
| 8.9.5 | PASS if form submission is keyboard-accessible (Enter to submit) | PASS/FAIL |
| 8.9.6 | PASS if tab order follows the visual layout of the form | PASS/FAIL |
| 8.9.7 | WARN if disabled fields do not have aria-disabled="true" | PASS/WARN |

## 8.10 Form Testing

| ID | Rule | Verdict |
|----|------|---------|
| 8.10.1 | WARN if Zod schemas do not have unit tests for valid and invalid inputs | PASS/WARN |
| 8.10.2 | FAIL if form component tests do not verify rendering of all expected fields and buttons | PASS/FAIL |
| 8.10.3 | FAIL if form tests do not verify validation error display on invalid submission | PASS/FAIL |
| 8.10.4 | WARN if form tests do not simulate server error mapping via handleApiError | PASS/WARN |
| 8.10.5 | FAIL if tests use fireEvent instead of userEvent for form interactions | PASS/FAIL |
| 8.10.6 | FAIL if tests do not verify that the mutation function is called with the expected payload on valid submission | PASS/FAIL |
| 8.10.7 | WARN if tests do not verify loading/disabled state during submission | PASS/WARN |
