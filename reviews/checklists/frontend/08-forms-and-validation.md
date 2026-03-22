# 08 — Forms & Validation Checklist

## 8.1 Form Library Consistency

- [ ] **All forms use react-hook-form with zodResolver** — every form in the application is built with useForm({ resolver: zodResolver(schema) }), no exceptions
- [ ] **No raw useState for form field management** — form field values, dirty state, and errors are managed exclusively by react-hook-form, not manual state variables
- [ ] **No mixing controlled and uncontrolled inputs within a form** — each form uses either register (uncontrolled) or Controller (controlled) consistently for all its fields
- [ ] **useForm configured with correct defaultValues and mode** — defaultValues match the expected initial state, mode is set to "onBlur" or "onChange" as appropriate for the form's UX
- [ ] **Form state from react-hook-form only** — isDirty, isSubmitting, isValid, and errors are read from the useForm return value, not derived from separate state
- [ ] **No competing form libraries** — no Formik, no custom form hooks, no other state management for form data anywhere in the codebase

## 8.2 Zod Validation Schemas

- [ ] **Schemas live in lib/validations/ or feature-specific files** — shared schemas (email, password, name) in lib/validations/, feature-specific schemas alongside their forms
- [ ] **Schemas match backend validation rules** — field lengths, patterns, required fields, and allowed values mirror the backend serializer constraints exactly
- [ ] **Zod refinements for complex validation** — password confirmation matching, date range validation (start < end), and conditional required fields use .refine() or .superRefine()
- [ ] **Schema types inferred with z.infer<typeof schema>** — form data types are derived from the Zod schema using type inference, not manually defined interfaces that could drift
- [ ] **Schemas reused across related forms** — create and edit forms share a base schema, extended or picked as needed, avoiding duplicated validation rules
- [ ] **No validation logic duplicated in components** — all validation rules live in Zod schemas, not in onSubmit handlers, onChange callbacks, or inline conditionals
- [ ] **Error messages are user-friendly** — Zod error messages use .message() to provide clear, non-technical descriptions of what the user needs to fix

## 8.3 Field Components

- [ ] **FormField wraps text inputs with label, description, and error display** — a consistent wrapper component provides the label-input-error layout for all text-based fields
- [ ] **FormTextarea wraps textarea with the same pattern** — multi-line text inputs follow the identical label-input-error layout as FormField for visual consistency
- [ ] **PasswordInput adds show/hide toggle with strength meter** — password fields include an eye icon toggle for visibility and an optional password strength indicator
- [ ] **FormTagInput handles array-type inputs** — tag fields allow adding and removing items, rendering them as chips/badges with validation on each tag
- [ ] **ComboboxField provides searchable dropdown** — cities, countries, and other large option sets use a combobox with typeahead filtering rather than a plain select
- [ ] **ImageUpload handles avatar and cover image with preview** — image fields show a preview of the selected file before submission, with clear and replace actions
- [ ] **All field components integrate with react-hook-form** — field components use register for simple inputs or Controller for complex components, passing field state and error state correctly

## 8.4 Error Display

- [ ] **Validation errors appear below the field they belong to** — each field's error message renders directly beneath the input, not in a separate error summary area
- [ ] **Server validation errors mapped to specific fields via handleApiError** — backend validation responses are parsed and each field error is applied using setError on the corresponding field name
- [ ] **Root-level errors show at form top** — non-field errors (general server errors, permission errors) display as an alert or banner above the form fields
- [ ] **Rate limiting shows countdown message** — when the server returns 429, the UI displays "Please wait X seconds" with a countdown timer
- [ ] **Field errors clear on user input** — errors disappear when the user starts editing the errored field, using mode: "onChange" or "onBlur" revalidation
- [ ] **Error messages are accessible** — aria-describedby links the error message element to its input, and screen readers announce the error when it appears
- [ ] **Multiple errors per field show the most relevant one** — when a field has multiple validation failures, only the highest-priority or first-matched error is displayed

## 8.5 Dynamic Form Builder

- [ ] **FormBuilder renders fields from template schema** — the FormBuilder component reads a form template definition and dynamically generates the appropriate field components
- [ ] **FieldRenderer handles all field types** — text, number, select, checkbox, radio, file upload, date picker, textarea, and other field types are all rendered correctly
- [ ] **FieldConfigPanel configures field properties** — template authors can set label, placeholder, required, validation rules, default value, and help text for each field
- [ ] **Field validation runs per-field-type** — text fields validate length and pattern, number fields validate range, select fields validate against allowed options
- [ ] **Drag-and-drop reordering of fields** — template authors can rearrange fields by dragging them to new positions within the form layout
- [ ] **Preview mode shows form as end user would see it** — a preview toggle renders the form template as it would appear to the person filling it out, with all styling applied
- [ ] **Form templates are versioned** — changes to a template create a new version, and existing responses reference the version they were submitted against

## 8.6 Form Submission

- [ ] **Submit handlers call mutation hooks** — form onSubmit delegates to a TanStack Query mutation hook (useMutation), not a direct API call or inline async function
- [ ] **Loading state disables submit button during submission** — the submit button shows a loading spinner and is disabled while isSubmitting or mutation.isPending is true
- [ ] **Success shows toast notification and/or navigates** — on successful submission, the user sees a success toast and is optionally navigated to the next page or back to a list
- [ ] **Errors are caught and displayed** — mutation errors are caught by the onError callback and displayed via handleApiError or a fallback toast message
- [ ] **No double submission** — the submit button is disabled during pending state and the form's onSubmit handler guards against re-entry while a submission is in progress
- [ ] **Form reset after successful submission where appropriate** — create forms reset to empty state after success, edit forms retain the updated values
- [ ] **Optimistic updates for inline edits** — quick edits (toggle, inline rename) use optimistic updates via TanStack Query's onMutate/onError/onSettled pattern

## 8.7 File Upload

- [ ] **ImageUpload component handles avatar and cover images** — a reusable component supports both circular avatar crops and rectangular cover image crops
- [ ] **File type validation runs client-side before upload** — the accept attribute limits the file picker, and Zod validates the file's MIME type before submission
- [ ] **File size validation runs client-side** — files exceeding the maximum size (configurable per use case) are rejected with a clear error message before any network request
- [ ] **Preview shown before submission** — selected files are displayed as a preview thumbnail using URL.createObjectURL, allowing the user to confirm before uploading
- [ ] **Upload progress indicated to user** — for large files, a progress bar or percentage indicator shows how much of the upload has completed
- [ ] **Uploaded file can be removed/replaced** — the user can clear the selected file and choose a different one, or remove the existing uploaded file

## 8.8 Complex Form Patterns

- [ ] **Multi-step forms maintain state across steps** — wizard-pattern forms preserve entered data when navigating between steps, not losing input on back/forward navigation
- [ ] **Conditional fields show/hide based on other field values** — fields that depend on another field's value (e.g., "Other" text input when "Other" is selected) appear and disappear dynamically
- [ ] **Form arrays for repeated field groups** — useFieldArray handles dynamic add/remove of repeated sections (phone numbers, addresses, team members)
- [ ] **Cross-field validation** — password confirmation must match password, end date must be after start date, and similar cross-field rules are enforced via Zod .refine()
- [ ] **Nested object forms** — address fields (street, city, country, postal code) are grouped as a nested object in the form schema and submitted as a structured object
- [ ] **Form state persisted on navigation away** — unsaved changes are detected and the user is warned before navigating away from a form with dirty state

## 8.9 Form Accessibility

- [ ] **Labels associated with inputs via htmlFor/id** — every input has a corresponding label element linked through matching htmlFor and id attributes
- [ ] **Required fields marked with visual indicator and aria-required** — required fields show an asterisk or similar visual cue and have aria-required="true" on the input
- [ ] **Error messages linked to fields via aria-describedby** — error message elements are connected to their input via aria-describedby so screen readers announce errors in context
- [ ] **Focus moves to first error on submission failure** — when form submission fails validation, focus is programmatically moved to the first field with an error
- [ ] **Form submission is keyboard-accessible** — pressing Enter in a text field or activating the submit button via keyboard triggers form submission
- [ ] **Tab order follows visual layout** — the tab sequence through form fields matches the visual top-to-bottom, left-to-right order of the form
- [ ] **Disabled fields have aria-disabled** — fields that are disabled (during loading, based on conditions) are marked with aria-disabled="true" for screen reader users

## 8.10 Form Testing

- [ ] **Zod schema validation unit tests** — each schema is tested with valid and invalid inputs to ensure rules are correctly defined
- [ ] **Form component tests verify rendering of all fields** — component tests confirm that all expected fields, labels, and buttons are rendered in the DOM
- [ ] **Form tests verify validation error display on submit** — submitting an empty or invalid form shows the correct error messages next to the right fields
- [ ] **Form tests verify server error mapping** — tests simulate backend validation errors and confirm they are correctly mapped to fields via handleApiError and setError
- [ ] **Tests use userEvent for realistic interactions** — @testing-library/user-event is used for typing, clicking, and tabbing rather than fireEvent for more realistic behavior
- [ ] **Tests verify submission calls the correct mutation** — after filling and submitting a valid form, tests assert that the mutation function was called with the expected payload
- [ ] **Tests verify loading/disabled state during submission** — tests confirm that the submit button is disabled and shows a loading indicator while the mutation is pending
