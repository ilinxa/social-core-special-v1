# shadcn/ui Customization

## Table of Contents
1. [How It Works](#how-it-works)
2. [Installation and Placement](#installation-and-placement)
3. [Theming](#theming)
4. [Customizing Components](#customizing-components)
5. [CVA (Class Variance Authority)](#cva)
6. [Icons](#icons)
7. [Form Components](#form-components)
8. [Keeping Updated](#keeping-updated)

---

## How It Works

shadcn/ui is a code generator, not a dependency. `npx shadcn@latest add button` copies source into your project. Stack: Radix UI (headless primitives), Tailwind (styling), CVA (variants), tailwind-merge + clsx (via `cn()`).

v4 stack: unified `radix-ui` package, OKLCH colors, `ref` as prop (React 19).
v3 stack: individual `@radix-ui/react-*` packages, HSL colors, `React.forwardRef`.

---

## Installation and Placement

```bash
npx shadcn@latest init    # project setup
npx shadcn@latest add button dialog input  # add components
```

Components live in `src/components/ui/`:
```
components/
├── ui/                 # shadcn primitives — minimal customization
│   ├── button.tsx
│   ├── dialog.tsx
│   └── input.tsx
├── common/             # Composed components using shadcn primitives
│   ├── ConfirmDialog.tsx
│   └── SearchInput.tsx
└── layout/
```

**`ui/` = shadcn source** (lowercase filenames, per shadcn convention). **`common/` = your compositions** (PascalCase, per ilinxa convention).

`components.json` — key settings:
```json
{
  "style": "new-york",
  "tailwind": { "config": "tailwind.config.ts", "css": "src/styles/globals.css" },
  "aliases": { "components": "@/components", "utils": "@/lib/utils" }
}
```

---

## Theming

CSS variables are the single source of truth. Customize colors by changing variable values, never by editing component files.

See [references/tailwind.md](tailwind.md) §shadcn CSS Variables for the full variable format (HSL for v3, OKLCH for v4).

Applying a brand theme: update CSS variables in `globals.css` root, use a tool like `ui.shadcn.com/themes` to generate a palette, keep semantic naming (background, foreground, primary, destructive).

---

## Customizing Components

### Safe: Modify the source (preferred)

```tsx
// src/components/ui/button.tsx — add ilinxa-specific defaults
const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        outline: "border border-input bg-background hover:bg-accent",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-md px-8",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);
```

### Adding custom variants

Add to the CVA config directly. Don't create wrapper components just for a new variant.

### Wrapping for extra behavior

When you need added props, state, or logic beyond styling:

```tsx
// src/components/common/ConfirmDialog.tsx
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

interface ConfirmDialogProps {
  title: string;
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
  open: boolean;
  destructive?: boolean;
}

export function ConfirmDialog({ title, message, onConfirm, onCancel, open, destructive }: ConfirmDialogProps) {
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onCancel()}>
      <DialogContent>
        <DialogHeader><DialogTitle>{title}</DialogTitle></DialogHeader>
        <p>{message}</p>
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onCancel}>Cancel</Button>
          <Button variant={destructive ? "destructive" : "default"} onClick={onConfirm}>Confirm</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
```

---

## CVA

```tsx
import { cva, type VariantProps } from "class-variance-authority";

const badgeVariants = cva(
  "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold", // base
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground",
        success: "bg-green-100 text-green-800",
        warning: "bg-yellow-100 text-yellow-800",
        error: "bg-red-100 text-red-800",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}
```

Add `tailwindFunctions: ["cn", "cva"]` to Prettier config for class sorting inside CVA.

---

## Icons

Use `lucide-react`. One icon per import, tree-shakeable:

```tsx
import { Search, ChevronDown, X } from "lucide-react";

<Button><Search className="mr-2 h-4 w-4" /> Search</Button>
```

Standard sizes: `h-4 w-4` (in buttons/inputs), `h-5 w-5` (standalone), `h-6 w-6` (large).

---

## Form Components

Use `react-hook-form` + Zod + shadcn Form components:

```tsx
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Form, FormField, FormItem, FormLabel, FormControl, FormMessage } from "@/components/ui/form";

const schema = z.object({ email: z.string().email(), name: z.string().min(2) });

export function ContactForm() {
  const form = useForm({ resolver: zodResolver(schema) });
  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)}>
        <FormField control={form.control} name="email" render={({ field }) => (
          <FormItem>
            <FormLabel>Email</FormLabel>
            <FormControl><Input {...field} /></FormControl>
            <FormMessage />
          </FormItem>
        )} />
      </form>
    </Form>
  );
}
```

---

## Keeping Updated

shadcn is source-owned. Updates are manual: `npx shadcn@latest diff` shows changes, then selectively apply. Document project's shadcn version in `components.json`. Track customizations with comments: `// ILINXA: added brand variant`.
