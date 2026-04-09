# E2E Coverage Matrix

> Auto-generated on 2026-03-27 by `scripts/generate-coverage-matrix.ts`
> **125 test files** | **465 tests**

## Layer Summary

| Layer | Files | Tests |
|-------|-------|-------|
| L1 | 89 | 236 |
| L2 | 28 | 30 |
| L3 | 8 | 199 |

## System x Parameter Matrix

Cell values show which test layers cover that system+parameter combination.
`-` = no coverage, `L1` = smoke only, `L1+L2` = smoke + workflow, etc.

| System | P1 | P2 | P3 | P4 | P5 | P6 | P7 | P8 | P9 | P10 | P11 | P12 | P13 | P14 |
|--------|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Auth** | L1+L2+L3 | L1+L2+L3 | L1+L2+L3 | L1+L2 | L1+L2+L3 | L3 | L1+L2+L3 | L1 | - | L1+L3 | L2+L3 | - | L3 | L1 |
| **Users** | L1+L2+L3 | L1+L2+L3 | L1+L2+L3 | L1 | L1+L3 | - | L1+L3 | - | - | - | L3 | - | L3 | L1 |
| **Organization** | L1+L2+L3 | L1+L2+L3 | L1+L2+L3 | L1+L2 | L1+L2+L3 | L2+L3 | L1+L2+L3 | L1+L2 | - | L1+L2+L3 | L2+L3 | - | L2+L3 | - |
| **Platform** | L2+L3 | L3 | - | - | L2+L3 | L2+L3 | - | L2 | - | - | L2 | - | - | - |
| **RBAC** | L1+L2+L3 | L1+L2+L3 | L2 | L1+L2 | L1+L2+L3 | L2+L3 | L1+L2 | - | - | L2+L3 | - | - | L2 | - |
| **Transaction** | L1+L2+L3 | L1+L2+L3 | L1+L2+L3 | L2 | L1+L2+L3 | L2+L3 | L3 | - | - | L2+L3 | - | - | - | - |
| **Forms** | L1+L3 | L1+L3 | L1 | L1+L2 | L1+L2+L3 | L2+L3 | - | - | - | L3 | - | - | - | - |
| **Chat** | L1+L2+L3 | L1+L3 | L1+L3 | - | L1+L2+L3 | L3 | L1+L2+L3 | L1 | - | - | - | - | - | L2 |
| **Network** | L1+L2+L3 | L1+L3 | L1+L3 | L2 | L1+L2+L3 | L3 | L2+L3 | L2 | - | - | - | - | - | - |
| **Explore** | L1+L2+L3 | L3 | L1+L3 | - | L1+L2+L3 | - | L3 | L2 | - | - | - | - | - | - |
| **CMS** | L1+L3 | L1+L3 | - | - | L1+L2+L3 | L2+L3 | - | - | - | - | - | - | - | - |
| **Notifications** | L1+L2 | L1 | L1 | - | L1+L2 | - | - | - | - | - | - | - | - | - |
| **Feature Gates** | L1 | - | - | - | L1 | L1 | - | - | - | - | - | - | - | L2 |
| **Visibility** | L1 | - | - | - | L1 | - | L1 | - | - | - | - | - | - | - |
| **Limits** | L1 | - | - | L1 | L1 | - | - | - | - | L1 | - | - | - | - |
| **Navigation** | L1 | L1 | L1 | - | - | - | - | L1 | - | - | - | - | - | - |
| **Public** | L1 | - | L1 | - | - | - | - | - | - | - | - | - | - | - |
| **Security** | L3 | - | - | - | L3 | - | - | - | - | - | L3 | - | L3 | - |

## Coverage: 113/252 cells (44.8%)

## Uncovered Cells

- **Auth** x **P9** (Visual Regression)
- **Auth** x **P12** (Accessibility)
- **Users** x **P6** (Real-Time)
- **Users** x **P8** (Responsive)
- **Users** x **P9** (Visual Regression)
- **Users** x **P10** (Limits & Quotas)
- **Users** x **P12** (Accessibility)
- **Organization** x **P9** (Visual Regression)
- **Organization** x **P12** (Accessibility)
- **Organization** x **P14** (State Persistence)
- **Platform** x **P3** (Navigation)
- **Platform** x **P4** (Data Accuracy)
- **Platform** x **P7** (Error Handling)
- **Platform** x **P9** (Visual Regression)
- **Platform** x **P10** (Limits & Quotas)
- **Platform** x **P12** (Accessibility)
- **Platform** x **P13** (Cross-User)
- **Platform** x **P14** (State Persistence)
- **RBAC** x **P8** (Responsive)
- **RBAC** x **P9** (Visual Regression)
- **RBAC** x **P11** (Security)
- **RBAC** x **P12** (Accessibility)
- **RBAC** x **P14** (State Persistence)
- **Transaction** x **P8** (Responsive)
- **Transaction** x **P9** (Visual Regression)
- **Transaction** x **P11** (Security)
- **Transaction** x **P12** (Accessibility)
- **Transaction** x **P13** (Cross-User)
- **Transaction** x **P14** (State Persistence)
- **Forms** x **P7** (Error Handling)
- **Forms** x **P8** (Responsive)
- **Forms** x **P9** (Visual Regression)
- **Forms** x **P11** (Security)
- **Forms** x **P12** (Accessibility)
- **Forms** x **P13** (Cross-User)
- **Forms** x **P14** (State Persistence)
- **Chat** x **P4** (Data Accuracy)
- **Chat** x **P9** (Visual Regression)
- **Chat** x **P10** (Limits & Quotas)
- **Chat** x **P11** (Security)
- **Chat** x **P12** (Accessibility)
- **Chat** x **P13** (Cross-User)
- **Network** x **P9** (Visual Regression)
- **Network** x **P10** (Limits & Quotas)
- **Network** x **P11** (Security)
- **Network** x **P12** (Accessibility)
- **Network** x **P13** (Cross-User)
- **Network** x **P14** (State Persistence)
- **Explore** x **P4** (Data Accuracy)
- **Explore** x **P6** (Real-Time)
- **Explore** x **P9** (Visual Regression)
- **Explore** x **P10** (Limits & Quotas)
- **Explore** x **P11** (Security)
- **Explore** x **P12** (Accessibility)
- **Explore** x **P13** (Cross-User)
- **Explore** x **P14** (State Persistence)
- **CMS** x **P3** (Navigation)
- **CMS** x **P4** (Data Accuracy)
- **CMS** x **P7** (Error Handling)
- **CMS** x **P8** (Responsive)
- **CMS** x **P9** (Visual Regression)
- **CMS** x **P10** (Limits & Quotas)
- **CMS** x **P11** (Security)
- **CMS** x **P12** (Accessibility)
- **CMS** x **P13** (Cross-User)
- **CMS** x **P14** (State Persistence)
- **Notifications** x **P4** (Data Accuracy)
- **Notifications** x **P6** (Real-Time)
- **Notifications** x **P7** (Error Handling)
- **Notifications** x **P8** (Responsive)
- **Notifications** x **P9** (Visual Regression)
- **Notifications** x **P10** (Limits & Quotas)
- **Notifications** x **P11** (Security)
- **Notifications** x **P12** (Accessibility)
- **Notifications** x **P13** (Cross-User)
- **Notifications** x **P14** (State Persistence)
- **Feature Gates** x **P2** (User Interaction)
- **Feature Gates** x **P3** (Navigation)
- **Feature Gates** x **P4** (Data Accuracy)
- **Feature Gates** x **P7** (Error Handling)
- **Feature Gates** x **P8** (Responsive)
- **Feature Gates** x **P9** (Visual Regression)
- **Feature Gates** x **P10** (Limits & Quotas)
- **Feature Gates** x **P11** (Security)
- **Feature Gates** x **P12** (Accessibility)
- **Feature Gates** x **P13** (Cross-User)
- **Visibility** x **P2** (User Interaction)
- **Visibility** x **P3** (Navigation)
- **Visibility** x **P4** (Data Accuracy)
- **Visibility** x **P6** (Real-Time)
- **Visibility** x **P8** (Responsive)
- **Visibility** x **P9** (Visual Regression)
- **Visibility** x **P10** (Limits & Quotas)
- **Visibility** x **P11** (Security)
- **Visibility** x **P12** (Accessibility)
- **Visibility** x **P13** (Cross-User)
- **Visibility** x **P14** (State Persistence)
- **Limits** x **P2** (User Interaction)
- **Limits** x **P3** (Navigation)
- **Limits** x **P6** (Real-Time)
- **Limits** x **P7** (Error Handling)
- **Limits** x **P8** (Responsive)
- **Limits** x **P9** (Visual Regression)
- **Limits** x **P11** (Security)
- **Limits** x **P12** (Accessibility)
- **Limits** x **P13** (Cross-User)
- **Limits** x **P14** (State Persistence)
- **Navigation** x **P4** (Data Accuracy)
- **Navigation** x **P5** (Auth & Authz)
- **Navigation** x **P6** (Real-Time)
- **Navigation** x **P7** (Error Handling)
- **Navigation** x **P9** (Visual Regression)
- **Navigation** x **P10** (Limits & Quotas)
- **Navigation** x **P11** (Security)
- **Navigation** x **P12** (Accessibility)
- **Navigation** x **P13** (Cross-User)
- **Navigation** x **P14** (State Persistence)
- **Public** x **P2** (User Interaction)
- **Public** x **P4** (Data Accuracy)
- **Public** x **P5** (Auth & Authz)
- **Public** x **P6** (Real-Time)
- **Public** x **P7** (Error Handling)
- **Public** x **P8** (Responsive)
- **Public** x **P9** (Visual Regression)
- **Public** x **P10** (Limits & Quotas)
- **Public** x **P11** (Security)
- **Public** x **P12** (Accessibility)
- **Public** x **P13** (Cross-User)
- **Public** x **P14** (State Persistence)
- **Security** x **P2** (User Interaction)
- **Security** x **P3** (Navigation)
- **Security** x **P4** (Data Accuracy)
- **Security** x **P6** (Real-Time)
- **Security** x **P7** (Error Handling)
- **Security** x **P8** (Responsive)
- **Security** x **P9** (Visual Regression)
- **Security** x **P10** (Limits & Quotas)
- **Security** x **P12** (Accessibility)
- **Security** x **P14** (State Persistence)
