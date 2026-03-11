# Component Architecture

## Table of Contents
1. [Size and Responsibility](#size-and-responsibility)
2. [Props](#props)
3. [Composition Patterns](#composition-patterns)
4. [State in Components](#state-in-components)
5. [Effects and Refs](#effects-and-refs)
6. [Component Checklist](#component-checklist)

---

## Size and Responsibility

**Single responsibility.** Signals a component is too large: >150 lines, >3 `useState`, fetches data AND renders complex UI, hard to name.

Three roles:
- **UI (presentational):** Receives props, renders JSX. No data fetching, no side effects.
- **Container:** Fetches data, manages state, passes to UI components.
- **Layout:** Structural — sidebars, grids, page shells. Contains slots via `children`.

---

## Props

```tsx
// ✅ Interface for props, destructure in signature
interface UserCardProps {
  user: User;
  onSelect: (id: string) => void;
  variant?: "compact" | "full";
}

export function UserCard({ user, onSelect, variant = "full" }: UserCardProps) {
  return <div>{user.name}</div>;
}
```

**Extending HTML attributes:**

```tsx
// ✅ Extend native element + add custom props
interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
}

export function Input({ label, error, className, ...rest }: InputProps) {
  return (
    <div>
      <label>{label}</label>
      <input className={cn("base-styles", className)} {...rest} />
      {error && <p className="text-destructive">{error}</p>}
    </div>
  );
}
```

**Avoid prop drilling (>2 levels).** Solutions: Zustand store, React context, or composition (pass components as props/children).

```tsx
// ❌ Prop drilling
<App user={user}> → <Dashboard user={user}> → <Sidebar user={user}> → <Avatar user={user}>

// ✅ Composition — pass the component, not data
<Dashboard sidebar={<Sidebar><Avatar user={user} /></Sidebar>} />
```

---

## Composition Patterns

### Children over configuration

```tsx
// ✅ Flexible — consumers control structure
<Card>
  <Card.Header>Title</Card.Header>
  <Card.Body>Content</Card.Body>
</Card>

// ❌ Configuration props — rigid
<Card title="Title" body="Content" showFooter={true} />
```

### Compound components

```tsx
function Tabs({ children }: { children: React.ReactNode }) {
  const [active, setActive] = useState(0);
  return <TabsContext.Provider value={{ active, setActive }}>{children}</TabsContext.Provider>;
}

Tabs.List = function TabList({ children }: { children: React.ReactNode }) { ... };
Tabs.Panel = function TabPanel({ children, index }: { children: React.ReactNode; index: number }) { ... };

// Usage
<Tabs>
  <Tabs.List><Tab>One</Tab><Tab>Two</Tab></Tabs.List>
  <Tabs.Panel index={0}>Content 1</Tabs.Panel>
  <Tabs.Panel index={1}>Content 2</Tabs.Panel>
</Tabs>
```

---

## State in Components

**Local state first.** Only lift when truly needed.

**Derived state — compute, don't store:**

```tsx
// ❌ Redundant state
const [items, setItems] = useState([]);
const [count, setCount] = useState(0);
useEffect(() => setCount(items.length), [items]); // unnecessary sync

// ✅ Compute
const count = items.length;
```

**Reducer for complex state:**

```tsx
type Action = { type: "increment" } | { type: "decrement" } | { type: "reset"; payload: number };

function reducer(state: number, action: Action): number {
  switch (action.type) {
    case "increment": return state + 1;
    case "decrement": return state - 1;
    case "reset": return action.payload;
  }
}
```

Use `useReducer` when: multiple related values, next state depends on previous, complex update logic.

---

## Effects and Refs

**Minimize `useEffect`.** Most "effects" are either derived state (compute it) or event handlers (use the handler directly).

Legitimate uses:
- Subscribing to external stores (WebSocket, browser APIs)
- Setting up event listeners that can't be attached via React
- Synchronizing with non-React systems (D3, maps, third-party widgets)
- One-time initialization

Always include cleanup:

```tsx
useEffect(() => {
  const controller = new AbortController();
  fetchData(controller.signal);
  return () => controller.abort(); // cleanup
}, [dependency]);
```

**Refs** for DOM access and mutable values that don't trigger re-renders:

```tsx
const inputRef = useRef<HTMLInputElement>(null);

// Focus programmatically
useEffect(() => { inputRef.current?.focus(); }, []);
```

---

## Component Checklist

- [ ] Single responsibility — does one thing
- [ ] Props typed with interface, destructured in signature
- [ ] No `React.FC`
- [ ] Named function declaration, named export
- [ ] No derived state stored in `useState`
- [ ] `useEffect` only for side effects, with cleanup
- [ ] <150 lines (including JSX)
- [ ] Accessible (semantic HTML, keyboard support)
