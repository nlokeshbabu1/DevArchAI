# DevArchAI - Enterprise SaaS Frontend Architecture

**Document Version:** 1.0  
**Date:** March 10, 2026  
**Status:** Production-Ready Specification

---

## Executive Summary

This document defines the complete frontend architecture for DevArchAI, an enterprise-grade SaaS platform for AI-powered DevOps architecture analysis. The frontend is designed to match the visual quality and user experience of modern DevOps platforms like GitHub, Vercel, Datadog, and HashiCorp Cloud.

---

## Table of Contents

1. [Product Capabilities Analysis](#1-product-capabilities-analysis)
2. [UX Design Principles](#2-ux-design-principles)
3. [Frontend Architecture](#3-frontend-architecture)
4. [Design System](#4-design-system)
5. [Component Library](#5-component-library)
6. [Page Specifications](#6-page-specifications)
7. [API Integration](#7-api-integration)
8. [Implementation Roadmap](#8-implementation-roadmap)

---

## 1. Product Capabilities Analysis

### 1.1 Core Platform Features

Based on codebase analysis, DevArchAI provides:

| Capability | Description | API Endpoint |
|------------|-------------|--------------|
| **Repository Analysis** | Scan GitHub repositories for DevOps configurations | `POST /api/v1/scans` |
| **Multi-Format Parsing** | Terraform, Kubernetes, Dockerfile, CI/CD | Internal service |
| **Security Analysis** | 20+ security rules (root containers, secrets, network policies) | Rule engine |
| **Scalability Analysis** | Resource limits, HPA, load balancing checks | Rule engine |
| **Reliability Analysis** | Health checks, backups, PDB validation | Rule engine |
| **Cost Optimization** | Right-sizing, spot instances, storage optimization | Rule engine |
| **Observability Analysis** | Monitoring, logging, alerting configuration | Rule engine |
| **AI Explanations** | LLM-powered insights and recommendations | `POST /api/v1/ai/analyze` |
| **Production Score** | 0-100 production readiness score | Scoring engine |
| **Report Generation** | JSON, PDF, Excel export | `GET /api/v1/reports/{id}/download` |

### 1.2 Data Models

```typescript
// Core entities extracted from backend schemas

interface Scan {
  id: string
  repository_url: string
  branch: string
  commit_hash?: string
  status: 'pending' | 'queued' | 'processing' | 'completed' | 'failed' | 'cancelled'
  progress: number
  overall_score?: number
  category_scores: CategoryScore[]
  created_at: string
  completed_at?: string
}

interface CategoryScore {
  category: 'security' | 'scalability' | 'reliability' | 'cost' | 'observability'
  score: number
  findings_count: number
  critical_count: number
  high_count: number
  medium_count: number
  low_count: number
}

interface Finding {
  rule_id: string
  rule_name: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  category: string
  description: string
  recommendation: string
  file_path?: string
  line_number?: number
  ai_explanation?: string
  impact_analysis?: string
  confidence_score: number
}

interface AnalysisReport {
  id: string
  repository_url: string
  repository_name: string
  commit_hash?: string
  created_at: string
  analysis_duration_seconds: number
  overall_score: number
  category_scores: CategoryScore[]
  findings: Finding[]
  summary: Record<string, number>
  executive_summary?: string
  risk_analysis?: string
  prioritized_recommendations?: string[]
  files_analyzed: string[]
}
```

### 1.3 Required API Endpoints for Frontend

```typescript
// Authentication
POST   /api/v1/auth/register          // User registration
POST   /api/v1/auth/login             // User login
POST   /api/v1/auth/logout            // User logout
POST   /api/v1/auth/refresh           // Refresh JWT token
GET    /api/v1/auth/me                // Get current user

// OAuth
POST   /api/v1/auth/github            // GitHub OAuth
POST   /api/v1/auth/google            // Google OAuth
POST   /api/v1/auth/microsoft         // Microsoft OAuth

// Scans
POST   /api/v1/scans                  // Create scan (authenticated)
POST   /api/v1/scans/analyze          // Create scan (anonymous)
GET    /api/v1/scans                  // List scans
GET    /api/v1/scans/:id              // Get scan details
GET    /api/v1/scans/:id/progress     // Get scan progress
POST   /api/v1/scans/:id/cancel       // Cancel scan

// Reports
GET    /api/v1/reports/:id            // Get report
GET    /api/v1/reports/:id/download   // Download report (json/pdf/excel)

// Repositories
GET    /api/v1/repositories           // List repositories
POST   /api/v1/repositories           // Add repository
DELETE /api/v1/repositories/:id       // Delete repository

// GitHub Integration
GET    /api/v1/github/branches/:owner/:repo  // List branches
GET    /api/v1/github/validate/:owner/:repo  // Validate repo access

// Health
GET    /api/v1/health                 // Health check
GET    /api/v1/health/ready           // Readiness check
GET    /api/v1/health/live            // Liveness check
```

---

## 2. UX Design Principles

### 2.1 Design Philosophy

DevArchAI follows enterprise DevOps platform UX patterns inspired by:

| Reference | Key Characteristics | Application to DevArchAI |
|-----------|---------------------|-------------------------|
| **GitHub** | Clean typography, subtle borders, monospace accents | Code snippets, file paths, commit hashes |
| **Vercel** | Bold gradients, geometric shapes, high contrast | Hero sections, CTAs, score visualizations |
| **Datadog** | Data-dense layouts, color-coded status, clear hierarchy | Dashboard, findings list, category scores |
| **HashiCorp** | Professional color palette, clear iconography | Navigation, feature cards, integration logos |

### 2.2 Core UX Principles

1. **Clarity Over Cleverness**
   - Use clear, direct language
   - Avoid ambiguous icons without labels
   - Show progress states explicitly

2. **Progressive Disclosure**
   - Show summary first, details on demand
   - Expandable findings with AI explanations
   - Layered navigation (global → section → detail)

3. **Immediate Feedback**
   - Optimistic UI updates
   - Real-time scan progress
   - Clear error states with recovery actions

4. **Enterprise Trust**
   - Professional visual design
   - Security indicators (SOC2, encryption)
   - Transparent data handling

5. **DevOps Efficiency**
   - Keyboard shortcuts for power users
   - Bulk actions for managing scans
   - Quick filters for findings

### 2.3 User Personas

| Persona | Role | Goals | Pain Points |
|---------|------|-------|-------------|
| **DevOps Lead (Sarah)** | Head of DevOps | Ensure production readiness, reduce incidents | Manual reviews, inconsistent configurations |
| **Platform Engineer (Mike)** | Infrastructure Engineer | Validate IaC before deployment | Time-consuming security reviews |
| **Security Engineer (Priya)** | DevSecOps | Find security misconfigurations | Too many false positives, lack of context |
| **CTO (David)** | Technology Executive | Understand risk posture, prioritize investments | Lack of visibility into technical debt |

---

## 3. Frontend Architecture

### 3.1 Technology Stack

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend Stack                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Framework: Next.js 14 (App Router)                             │
│  Language:  TypeScript 5.3+                                     │
│  Styling:   Tailwind CSS 3.4 + CSS Variables                    │
│  Components: React 18 + Radix UI Primitives                     │
│  State:     Zustand (client) + React Query (server)             │
│  Forms:     React Hook Form + Zod validation                    │
│  Charts:    Recharts + Nivo                                     │
│  Icons:     Lucide React + Custom SVG                           │
│  Build:     Turbopack                                           │
│  Testing:   Vitest + React Testing Library + Playwright         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Recommended Folder Structure

```
frontend/
├── public/
│   ├── fonts/
│   ├── images/
│   │   ├── logos/
│   │   │   ├── aws.svg
│   │   │   ├── kubernetes.svg
│   │   │   ├── terraform.svg
│   │   │   ├── github.svg
│   │   │   └── docker.svg
│   │   └── illustrations/
│   │       └── hero-analysis.svg
│   └── icons/
│       └── favicon.svg
│
├── src/
│   ├── app/                          # Next.js App Router
│   │   ├── (marketing)/              # Marketing routes
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx              # Landing page
│   │   │   ├── pricing/
│   │   │   └── features/
│   │   ├── (auth)/                   # Auth routes
│   │   │   ├── layout.tsx
│   │   │   ├── login/
│   │   │   ├── register/
│   │   │   └── forgot-password/
│   │   ├── (dashboard)/              # App routes (protected)
│   │   │   ├── layout.tsx
│   │   │   ├── dashboard/
│   │   │   ├── scans/
│   │   │   │   ├── page.tsx
│   │   │   │   └── [id]/
│   │   │   ├── reports/
│   │   │   │   ├── page.tsx
│   │   │   │   └── [id]/
│   │   │   ├── repositories/
│   │   │   ├── findings/
│   │   │   ├── settings/
│   │   │   └── billing/
│   │   ├── api/                      # API routes (optional BFF)
│   │   ├── layout.tsx                # Root layout
│   │   ├── providers.tsx             # Context providers
│   │   └── globals.css               # Global styles
│   │
│   ├── components/
│   │   ├── ui/                       # Base UI components
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── input.tsx
│   │   │   ├── select.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── toast.tsx
│   │   │   ├── progress.tsx
│   │   │   ├── badge.tsx
│   │   │   ├── avatar.tsx
│   │   │   ├── dropdown-menu.tsx
│   │   │   ├── tabs.tsx
│   │   │   ├── skeleton.tsx
│   │   │   └── tooltip.tsx
│   │   │
│   │   ├── marketing/                # Marketing components
│   │   │   ├── navbar.tsx
│   │   │   ├── footer.tsx
│   │   │   ├── hero-section.tsx
│   │   │   ├── features-grid.tsx
│   │   │   ├── integration-logos.tsx
│   │   │   ├── pricing-cards.tsx
│   │   │   ├── testimonial-carousel.tsx
│   │   │   └── cta-section.tsx
│   │   │
│   │   ├── auth/                     # Auth components
│   │   │   ├── login-form.tsx
│   │   │   ├── register-form.tsx
│   │   │   ├── forgot-password-form.tsx
│   │   │   ├── oauth-buttons.tsx
│   │   │   └── auth-layout.tsx
│   │   │
│   │   ├── dashboard/                # Dashboard components
│   │   │   ├── app-navbar.tsx
│   │   │   ├── sidebar.tsx
│   │   │   ├── overview-cards.tsx
│   │   │   ├── recent-scans.tsx
│   │   │   ├── score-gauge.tsx
│   │   │   └── activity-chart.tsx
│   │   │
│   │   ├── scans/                    # Scan components
│   │   │   ├── scan-input.tsx
│   │   │   ├── scan-progress.tsx
│   │   │   ├── scan-list.tsx
│   │   │   ├── scan-card.tsx
│   │   │   └── branch-selector.tsx
│   │   │
│   │   ├── reports/                  # Report components
│   │   │   ├── report-header.tsx
│   │   │   ├── score-overview.tsx
│   │   │   ├── category-radar.tsx
│   │   │   ├── findings-list.tsx
│   │   │   ├── finding-card.tsx
│   │   │   ├── finding-detail.tsx
│   │   │   ├── executive-summary.tsx
│   │   │   └── export-buttons.tsx
│   │   │
│   │   ├── repositories/             # Repository components
│   │   │   ├── repo-list.tsx
│   │   │   ├── repo-card.tsx
│   │   │   └── repo-add-dialog.tsx
│   │   │
│   │   └── findings/                 # Findings components
│   │       ├── findings-table.tsx
│   │       ├── findings-filters.tsx
│   │       └── severity-badge.tsx
│   │
│   ├── lib/
│   │   ├── utils.ts                  # Utility functions
│   │   ├── cn.ts                     # Class name merger
│   │   ├── formatters.ts             # Date, number formatters
│   │   └── constants.ts              # App constants
│   │
│   ├── hooks/
│   │   ├── use-auth.ts               # Auth hook
│   │   ├── use-scans.ts              # Scans hook
│   │   ├── use-reports.ts            # Reports hook
│   │   ├── use-repositories.ts       # Repositories hook
│   │   └── use-toast.ts              # Toast notifications
│   │
│   ├── services/
│   │   ├── api.ts                    # API client (axios/fetch)
│   │   ├── auth.ts                   # Auth service
│   │   ├── scans.ts                  # Scans service
│   │   ├── reports.ts                # Reports service
│   │   └── repositories.ts           # Repositories service
│   │
│   ├── stores/
│   │   ├── auth-store.ts             # Auth state (Zustand)
│   │   ├── ui-store.ts               # UI state (Zustand)
│   │   └── scan-store.ts             # Scan state (Zustand)
│   │
│   ├── types/
│   │   ├── api.ts                    # API types
│   │   ├── models.ts                 # Data models
│   │   └── index.ts                  # Type exports
│   │
│   ├── utils/
│   │   ├── validation.ts             # Zod schemas
│   │   ├── security.ts               # Security utilities
│   │   └── analytics.ts              # Analytics tracking
│   │
│   └── config/
│       ├── site.ts                   # Site configuration
│       ├── navigation.ts             # Navigation config
│       └── api.ts                    # API configuration
│
├── tests/
│   ├── components/
│   ├── pages/
│   ├── e2e/
│   └── fixtures/
│
├── .env.local
├── .env.example
├── next.config.js
├── tailwind.config.ts
├── tsconfig.json
├── package.json
└── README.md
```

### 3.3 Project Configuration

#### package.json Dependencies

```json
{
  "name": "devarchai-frontend",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "test": "vitest",
    "test:e2e": "playwright test",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "next": "14.1.0",
    "react": "18.2.0",
    "react-dom": "18.2.0",
    "@radix-ui/react-dialog": "1.0.5",
    "@radix-ui/react-dropdown-menu": "2.0.6",
    "@radix-ui/react-select": "2.0.0",
    "@radix-ui/react-tabs": "1.0.4",
    "@radix-ui/react-tooltip": "1.0.7",
    "@radix-ui/react-progress": "1.0.3",
    "@radix-ui/react-avatar": "1.0.4",
    "@tanstack/react-query": "5.17.9",
    "@hookform/resolvers": "3.3.4",
    "zod": "3.22.4",
    "react-hook-form": "7.49.3",
    "zustand": "4.5.0",
    "axios": "1.6.5",
    "recharts": "2.10.4",
    "@nivo/radar": "0.84.0",
    "@nivo/pie": "0.84.0",
    "lucide-react": "0.312.0",
    "clsx": "2.1.0",
    "tailwind-merge": "2.2.0",
    "date-fns": "3.3.1",
    "framer-motion": "10.18.0"
  },
  "devDependencies": {
    "@types/node": "20.11.5",
    "@types/react": "18.2.48",
    "@types/react-dom": "18.2.18",
    "typescript": "5.3.3",
    "tailwindcss": "3.4.1",
    "autoprefixer": "10.4.17",
    "postcss": "8.4.33",
    "eslint": "8.56.0",
    "eslint-config-next": "14.1.0",
    "vitest": "1.2.1",
    "@testing-library/react": "14.1.2",
    "@playwright/test": "1.41.1"
  }
}
```

---

## 4. Design System

### 4.1 Color Palette

```typescript
// tailwind.config.ts - Color System
{
  theme: {
    extend: {
      colors: {
        // Primary brand colors (DevOps purple/blue)
        primary: {
          50: '#f5f3ff',
          100: '#ede9fe',
          200: '#ddd6fe',
          300: '#c4b5fd',
          400: '#a78bfa',
          500: '#8b5cf6',  // Main primary
          600: '#7c3aed',  // Hover primary
          700: '#6d28d9',
          800: '#5b21b6',
          900: '#4c1d95',
          950: '#2e1065',
        },
        
        // Secondary accent (cyan/teal for DevOps feel)
        secondary: {
          50: '#f0fdfa',
          100: '#ccfbf1',
          200: '#99f6e4',
          300: '#5eead4',
          400: '#2dd4bf',
          500: '#14b8a6',  // Main secondary
          600: '#0d9488',
          700: '#0f766e',
          800: '#115e59',
          900: '#134e4a',
        },
        
        // Semantic colors
        success: {
          50: '#f0fdf4',
          100: '#dcfce7',
          500: '#22c55e',
          600: '#16a34a',
          700: '#15803d',
        },
        warning: {
          50: '#fffbeb',
          100: '#fef3c7',
          500: '#eab308',
          600: '#ca8a04',
          700: '#a16207',
        },
        error: {
          50: '#fef2f2',
          100: '#fee2e2',
          500: '#ef4444',
          600: '#dc2626',
          700: '#b91c1c',
        },
        info: {
          50: '#eff6ff',
          100: '#dbeafe',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
        },
        
        // Neutral grays
        gray: {
          50: '#f9fafb',
          100: '#f3f4f6',
          200: '#e5e7eb',
          300: '#d1d5db',
          400: '#9ca3af',
          500: '#6b7280',
          600: '#4b5563',
          700: '#374151',
          800: '#1f2937',
          900: '#111827',
          950: '#030712',
        },
      },
    },
  },
}
```

### 4.2 Severity Colors (for Findings)

```typescript
const severityColors = {
  critical: {
    bg: 'bg-red-500/10',
    border: 'border-red-500/30',
    text: 'text-red-600',
    badge: 'bg-red-500 text-white',
  },
  high: {
    bg: 'bg-orange-500/10',
    border: 'border-orange-500/30',
    text: 'text-orange-600',
    badge: 'bg-orange-500 text-white',
  },
  medium: {
    bg: 'bg-yellow-500/10',
    border: 'border-yellow-500/30',
    text: 'text-yellow-700',
    badge: 'bg-yellow-500 text-white',
  },
  low: {
    bg: 'bg-green-500/10',
    border: 'border-green-500/30',
    text: 'text-green-600',
    badge: 'bg-green-500 text-white',
  },
  info: {
    bg: 'bg-blue-500/10',
    border: 'border-blue-500/30',
    text: 'text-blue-600',
    badge: 'bg-blue-500 text-white',
  },
}
```

### 4.3 Typography

```typescript
// tailwind.config.ts - Typography
{
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      fontSize: {
        '2xs': ['0.625rem', { lineHeight: '0.875rem' }],
        xs: ['0.75rem', { lineHeight: '1rem' }],
        sm: ['0.875rem', { lineHeight: '1.25rem' }],
        base: ['1rem', { lineHeight: '1.5rem' }],
        lg: ['1.125rem', { lineHeight: '1.75rem' }],
        xl: ['1.25rem', { lineHeight: '1.75rem' }],
        '2xl': ['1.5rem', { lineHeight: '2rem' }],
        '3xl': ['1.875rem', { lineHeight: '2.25rem' }],
        '4xl': ['2.25rem', { lineHeight: '2.5rem' }],
        '5xl': ['3rem', { lineHeight: '1' }],
        '6xl': ['3.75rem', { lineHeight: '1' }],
      },
    },
  },
}
```

### 4.4 Spacing & Layout

```typescript
// Standard spacing scale (Tailwind default)
// 4px base unit: 1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 24, 32, 40, 48, 56, 64, 80, 96

// Container widths
{
  maxWidth: {
    '4xl': '80rem',
    '5xl': '90rem',
    '6xl': '96rem',
    '7xl': '108rem',
  },
}
```

### 4.5 Shadows & Elevation

```typescript
{
  boxShadow: {
    sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
    DEFAULT: '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
    md: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
    lg: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
    xl: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
    '2xl': '0 25px 50px -12px rgb(0 0 0 / 0.25)',
    inner: 'inset 0 2px 4px 0 rgb(0 0 0 / 0.05)',
    
    // Brand shadows
    'primary-glow': '0 0 20px rgb(139 92 246 / 0.3)',
    'primary-shadow': '0 4px 14px 0 rgb(139 92 246 / 0.39)',
  },
}
```

### 4.6 Border Radius

```typescript
{
  borderRadius: {
    none: '0',
    sm: '0.25rem',
    DEFAULT: '0.375rem',
    md: '0.5rem',
    lg: '0.75rem',
    xl: '1rem',
    '2xl': '1.25rem',
    '3xl': '1.5rem',
    full: '9999px',
  },
}
```

### 4.7 Animations & Transitions

```typescript
{
  animation: {
    'fade-in': 'fadeIn 0.3s ease-in-out',
    'fade-in-delayed': 'fadeIn 0.5s ease-in-out 0.2s both',
    'slide-up': 'slideUp 0.4s ease-out',
    'slide-down': 'slideDown 0.4s ease-out',
    'scale-in': 'scaleIn 0.2s ease-out',
    'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
    'spin-slow': 'spin 2s linear infinite',
    bounce: 'bounce 1s infinite',
  },
  keyframes: {
    fadeIn: {
      '0%': { opacity: '0' },
      '100%': { opacity: '1' },
    },
    slideUp: {
      '0%': { transform: 'translateY(10px)', opacity: '0' },
      '100%': { transform: 'translateY(0)', opacity: '1' },
    },
    slideDown: {
      '0%': { transform: 'translateY(-10px)', opacity: '0' },
      '100%': { transform: 'translateY(0)', opacity: '1' },
    },
    scaleIn: {
      '0%': { transform: 'scale(0.95)', opacity: '0' },
      '100%': { transform: 'scale(1)', opacity: '1' },
    },
  },
  transitionDuration: {
    75: '75ms',
    100: '100ms',
    150: '150ms',
    200: '200ms',
    300: '300ms',
    500: '500ms',
    700: '700ms',
    1000: '1000ms',
  },
}
```

### 4.8 Dark Mode Support

```typescript
// tailwind.config.ts
{
  darkMode: 'class',
  // Use class strategy for manual toggle
}

// CSS variables for theme switching
:root {
  --background: 0 0% 100%;
  --foreground: 222.2 84% 4.9%;
  --card: 0 0% 100%;
  --card-foreground: 222.2 84% 4.9%;
  --popover: 0 0% 100%;
  --popover-foreground: 222.2 84% 4.9%;
  --primary: 262 83% 58%;
  --primary-foreground: 210 40% 98%;
  --secondary: 174 72% 56%;
  --secondary-foreground: 222.2 47.4% 11.2%;
  --muted: 210 40% 96.1%;
  --muted-foreground: 215.4 16.3% 46.9%;
  --accent: 210 40% 96.1%;
  --accent-foreground: 222.2 47.4% 11.2%;
  --destructive: 0 84.2% 60.2%;
  --destructive-foreground: 210 40% 98%;
  --border: 214.3 31.8% 91.4%;
  --input: 214.3 31.8% 91.4%;
  --ring: 262 83% 58%;
}

.dark {
  --background: 222.2 84% 4.9%;
  --foreground: 210 40% 98%;
  --card: 222.2 84% 4.9%;
  --card-foreground: 210 40% 98%;
  --popover: 222.2 84% 4.9%;
  --popover-foreground: 210 40% 98%;
  --primary: 262 83% 58%;
  --primary-foreground: 210 40% 98%;
  --secondary: 174 72% 56%;
  --secondary-foreground: 210 40% 98%;
  --muted: 217.2 32.6% 17.5%;
  --muted-foreground: 215 20.2% 65.1%;
  --accent: 217.2 32.6% 17.5%;
  --accent-foreground: 210 40% 98%;
  --destructive: 0 62.8% 30.6%;
  --destructive-foreground: 210 40% 98%;
  --border: 217.2 32.6% 17.5%;
  --input: 217.2 32.6% 17.5%;
  --ring: 262 83% 58%;
}
```

---

## 5. Component Library

### 5.1 Base UI Components

#### Button Component

```tsx
// src/components/ui/button.tsx
import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'
import { Loader2 } from 'lucide-react'

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        primary: 'bg-primary-600 text-white hover:bg-primary-700 shadow-primary-shadow',
        secondary: 'bg-secondary-500 text-white hover:bg-secondary-600',
        outline: 'border-2 border-gray-300 bg-transparent hover:bg-gray-100 text-gray-900',
        ghost: 'hover:bg-gray-100 text-gray-700',
        link: 'text-primary-600 underline-offset-4 hover:underline',
        destructive: 'bg-error-600 text-white hover:bg-error-700',
      },
      size: {
        sm: 'h-9 px-3 text-sm',
        md: 'h-10 px-4 text-sm',
        lg: 'h-11 px-6 text-base',
        xl: 'h-12 px-8 text-lg',
        icon: 'h-10 w-10',
      },
      glow: {
        true: 'hover:shadow-primary-glow',
        false: '',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
      glow: false,
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  isLoading?: boolean
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, glow, isLoading, leftIcon, rightIcon, children, disabled, ...props }, ref) => {
    return (
      <button
        className={cn(buttonVariants({ variant, size, glow, className }))}
        ref={ref}
        disabled={disabled || isLoading}
        {...props}
      >
        {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
        {!isLoading && leftIcon && <span className="h-4 w-4">{leftIcon}</span>}
        {children}
        {!isLoading && rightIcon && <span className="h-4 w-4">{rightIcon}</span>}
      </button>
    )
  }
)
Button.displayName = 'Button'

export { Button, buttonVariants }
```

#### Card Component

```tsx
// src/components/ui/card.tsx
import * as React from 'react'
import { cn } from '@/lib/utils'

const Card = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement> & { hover?: boolean }>(
  ({ className, hover = false, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        'rounded-xl border bg-card text-card-foreground shadow-sm',
        hover && 'transition-all duration-300 hover:shadow-lg hover:border-primary/30',
        className
      )}
      {...props}
    />
  )
)
Card.displayName = 'Card'

const CardHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('flex flex-col space-y-1.5 p-6', className)} {...props} />
  )
)
CardHeader.displayName = 'CardHeader'

const CardTitle = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLHeadingElement>>(
  ({ className, ...props }, ref) => (
    <h3 ref={ref} className={cn('text-lg font-semibold leading-none tracking-tight', className)} {...props} />
  )
)
CardTitle.displayName = 'CardTitle'

const CardDescription = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLParagraphElement>>(
  ({ className, ...props }, ref) => (
    <p ref={ref} className={cn('text-sm text-muted-foreground', className)} {...props} />
  )
)
CardDescription.displayName = 'CardDescription'

const CardContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('p-6 pt-0', className)} {...props} />
  )
)
CardContent.displayName = 'CardContent'

const CardFooter = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('flex items-center p-6 pt-0', className)} {...props} />
  )
)
CardFooter.displayName = 'CardFooter'

export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent }
```

#### Badge Component

```tsx
// src/components/ui/badge.tsx
import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
  {
    variants: {
      variant: {
        default: 'border-transparent bg-primary-100 text-primary-700',
        secondary: 'border-transparent bg-secondary-100 text-secondary-700',
        outline: 'text-foreground',
        success: 'border-transparent bg-success-100 text-success-700',
        warning: 'border-transparent bg-warning-100 text-warning-700',
        error: 'border-transparent bg-error-100 text-error-700',
        info: 'border-transparent bg-info-100 text-info-700',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
)

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />
}

export { Badge, badgeVariants }
```

### 5.2 Marketing Components

#### Navbar Component

```tsx
// src/components/marketing/navbar.tsx
'use client'

import { useState } from 'react'
import Link from 'next/link'
import { motion, AnimatePresence } from 'framer-motion'
import { Shield, Menu, X, ChevronDown } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

const navLinks = [
  {
    label: 'Product',
    href: '/features',
    dropdown: ['Features', 'Integrations', 'Security', 'Changelog'],
  },
  { label: 'Features', href: '/features' },
  { label: 'Security', href: '/security' },
  { label: 'Pricing', href: '/pricing' },
  { label: 'Documentation', href: '/docs' },
]

export function Navbar() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)
  const [activeDropdown, setActiveDropdown] = useState<string | null>(null)

  return (
    <header className="sticky top-0 z-50 w-full border-b border-gray-200 bg-white/80 backdrop-blur-xl">
      <nav className="container mx-auto px-4">
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary-600 to-indigo-600 shadow-lg shadow-primary-500/30">
              <Shield className="h-6 w-6 text-white" />
            </div>
            <span className="text-xl font-bold bg-gradient-to-r from-primary-600 to-indigo-600 bg-clip-text text-transparent">
              DevArchAI
            </span>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-8">
            {navLinks.map((link) => (
              <div
                key={link.label}
                className="relative"
                onMouseEnter={() => link.dropdown && setActiveDropdown(link.label)}
                onMouseLeave={() => setActiveDropdown(null)}
              >
                <Link
                  href={link.href}
                  className="flex items-center gap-1 text-sm font-medium text-gray-700 hover:text-primary-600 transition-colors"
                >
                  {link.label}
                  {link.dropdown && <ChevronDown className="h-4 w-4" />}
                </Link>

                {/* Dropdown */}
                <AnimatePresence>
                  {activeDropdown === link.label && link.dropdown && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: 10 }}
                      className="absolute top-full left-0 pt-2"
                    >
                      <div className="rounded-xl border border-gray-200 bg-white shadow-xl p-2 min-w-[200px]">
                        {link.dropdown.map((item) => (
                          <Link
                            key={item}
                            href={`/features/${item.toLowerCase()}`}
                            className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                          >
                            {item}
                          </Link>
                        ))}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            ))}
          </div>

          {/* Auth Buttons */}
          <div className="hidden md:flex items-center gap-4">
            <Button variant="ghost" size="sm" asChild>
              <Link href="/login">Login</Link>
            </Button>
            <Button variant="primary" size="sm" glow asChild>
              <Link href="/register">Get Started</Link>
            </Button>
          </div>

          {/* Mobile Menu Button */}
          <button
            className="md:hidden p-2 text-gray-700"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          >
            {isMobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </div>

        {/* Mobile Menu */}
        <AnimatePresence>
          {isMobileMenuOpen && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="md:hidden border-t border-gray-200 py-4"
            >
              <div className="flex flex-col gap-4">
                {navLinks.map((link) => (
                  <Link
                    key={link.label}
                    href={link.href}
                    className="text-sm font-medium text-gray-700 hover:text-primary-600"
                  >
                    {link.label}
                  </Link>
                ))}
                <div className="flex flex-col gap-2 pt-4 border-t border-gray-200">
                  <Button variant="ghost" size="sm" asChild>
                    <Link href="/login">Login</Link>
                  </Button>
                  <Button variant="primary" size="sm" glow asChild>
                    <Link href="/register">Get Started</Link>
                  </Button>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </nav>
    </header>
  )
}
```

#### Hero Section

```tsx
// src/components/marketing/hero-section.tsx
'use client'

import { motion } from 'framer-motion'
import { ArrowRight, Sparkles, Check } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import Link from 'next/link'

const animationSteps = [
  { text: 'Connecting to GitHub repository...', icon: '🔗' },
  { text: 'Detecting DevOps stack...', icon: '🔍' },
  { text: 'Scanning Docker, Terraform, CI/CD...', icon: '📁' },
  { text: 'Running security checks...', icon: '🛡️' },
  { text: 'Generating AI recommendations...', icon: '✨' },
]

export function HeroSection() {
  return (
    <section className="relative py-20 lg:py-32 overflow-hidden">
      {/* Background gradients */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-96 h-96 bg-primary-500/20 rounded-full blur-3xl" />
        <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-indigo-600/20 rounded-full blur-3xl" />
      </div>

      <div className="container mx-auto px-4 relative">
        <div className="max-w-4xl mx-auto text-center space-y-8">
          {/* Badge */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary-100 border border-primary-300 backdrop-blur-sm shadow-lg shadow-primary-500/20"
          >
            <Sparkles className="h-4 w-4 text-primary-600" />
            <span className="text-sm font-medium text-primary-700">
              AI-Powered DevOps Architecture Analyzer
            </span>
          </motion.div>

          {/* Title */}
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-4xl md:text-6xl lg:text-7xl font-bold tracking-tight"
          >
            <span className="bg-gradient-to-r from-primary-600 to-indigo-600 bg-clip-text text-transparent">
              Analyze Your DevOps
            </span>
            <br />
            <span className="text-gray-900">Architecture in Seconds</span>
          </motion.h1>

          {/* Description */}
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="text-lg md:text-xl text-gray-600 max-w-2xl mx-auto"
          >
            Analyze GitHub repositories to detect infrastructure issues in Docker, Terraform,
            Kubernetes, and CI/CD pipelines. Get AI-powered recommendations for production readiness.
          </motion.p>

          {/* CTA Buttons */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="flex flex-col sm:flex-row items-center justify-center gap-4"
          >
            <Button variant="primary" size="lg" glow asChild className="w-full sm:w-auto px-8 py-6 text-lg">
              <Link href="/register">
                Start Free Analysis
                <ArrowRight className="h-5 w-5 ml-2" />
              </Link>
            </Button>
            <Button variant="outline" size="lg" asChild className="w-full sm:w-auto px-8 py-6 text-lg">
              <Link href="/demo">Book Demo</Link>
            </Button>
          </motion.div>

          {/* Animation Demo */}
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="mt-12 max-w-2xl mx-auto"
          >
            <Card className="p-6" hover>
              <div className="space-y-4">
                <h3 className="text-sm font-medium text-gray-500 text-left">Live Analysis Demo</h3>
                <div className="space-y-3">
                  {animationSteps.map((step, index) => (
                    <div
                      key={index}
                      className="flex items-center gap-3 p-3 rounded-lg bg-gray-50 border border-gray-200"
                    >
                      <span className="text-xl">{step.icon}</span>
                      <span className="text-sm font-medium text-gray-700">{step.text}</span>
                      {index === 0 && (
                        <div className="ml-auto">
                          <div className="w-4 h-4 border-2 border-primary-300 border-t-primary-600 rounded-full animate-spin" />
                        </div>
                      )}
                      {index > 0 && <Check className="h-4 w-4 text-green-500 ml-auto" />}
                    </div>
                  ))}
                </div>
              </div>
            </Card>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
```

#### Integration Logos Grid

```tsx
// src/components/marketing/integration-logos.tsx
'use client'

import { motion } from 'framer-motion'

const integrations = [
  { name: 'GitHub', icon: '/images/logos/github.svg', color: '#181717' },
  { name: 'Kubernetes', icon: '/images/logos/kubernetes.svg', color: '#326CE5' },
  { name: 'Terraform', icon: '/images/logos/terraform.svg', color: '#7B42BC' },
  { name: 'Docker', icon: '/images/logos/docker.svg', color: '#2496ED' },
  { name: 'AWS', icon: '/images/logos/aws.svg', color: '#FF9900' },
  { name: 'Azure', icon: '/images/logos/azure.svg', color: '#0078D4' },
  { name: 'GCP', icon: '/images/logos/gcp.svg', color: '#4285F4' },
  { name: 'GitLab', icon: '/images/logos/gitlab.svg', color: '#FC6D26' },
]

export function IntegrationLogos() {
  return (
    <section className="py-16 border-y border-gray-200 bg-gray-50">
      <div className="container mx-auto px-4">
        <p className="text-center text-sm font-medium text-gray-500 mb-8">
          INTEGRATES WITH YOUR DEVOPS STACK
        </p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 max-w-4xl mx-auto">
          {integrations.map((integration, index) => (
            <motion.div
              key={integration.name}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              className="flex items-center justify-center p-4 rounded-xl bg-white border border-gray-200 shadow-sm hover:shadow-md transition-shadow"
            >
              <img
                src={integration.icon}
                alt={integration.name}
                className="h-8 w-auto object-contain"
                style={{ filter: `grayscale(100%) opacity(0.6)` }}
              />
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
```

#### Pricing Cards

```tsx
// src/components/marketing/pricing-cards.tsx
'use client'

import { Check } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import Link from 'next/link'

const plans = [
  {
    name: 'Free',
    description: 'For individuals and small projects',
    price: '$0',
    period: '/month',
    features: [
      '10 scans per month',
      'Basic security checks',
      'Community support',
      'Public repositories only',
      'JSON report export',
    ],
    cta: 'Start Free',
    popular: false,
  },
  {
    name: 'Pro',
    description: 'For growing teams and startups',
    price: '$49',
    period: '/month',
    features: [
      'Unlimited scans',
      'All security checks',
      'AI-powered recommendations',
      'Private repositories',
      'PDF & Excel export',
      'Priority support',
      'Team collaboration',
    ],
    cta: 'Start Pro Trial',
    popular: true,
  },
  {
    name: 'Enterprise',
    description: 'For large organizations',
    price: 'Custom',
    period: '',
    features: [
      'Everything in Pro',
      'SSO & SAML',
      'Custom integrations',
      'Dedicated support',
      'SLA guarantees',
      'On-premise deployment',
      'Custom compliance rules',
    ],
    cta: 'Contact Sales',
    popular: false,
  },
]

export function PricingCards() {
  return (
    <section className="py-20 lg:py-32">
      <div className="container mx-auto px-4">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold mb-4">
            <span className="bg-gradient-to-r from-primary-600 to-indigo-600 bg-clip-text text-transparent">
              Simple, Transparent Pricing
            </span>
          </h2>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Start free and scale as you grow. No credit card required.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto">
          {plans.map((plan) => (
            <Card
              key={plan.name}
              className={`relative p-8 ${
                plan.popular
                  ? 'border-primary-500 shadow-xl scale-105'
                  : 'border-gray-200'
              }`}
              hover
            >
              {plan.popular && (
                <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                  <span className="bg-gradient-to-r from-primary-600 to-indigo-600 text-white text-sm font-medium px-4 py-1 rounded-full">
                    Most Popular
                  </span>
                </div>
              )}

              <div className="space-y-6">
                <div>
                  <h3 className="text-xl font-semibold text-gray-900">{plan.name}</h3>
                  <p className="text-sm text-gray-600 mt-1">{plan.description}</p>
                </div>

                <div>
                  <span className="text-4xl font-bold text-gray-900">{plan.price}</span>
                  <span className="text-gray-600">{plan.period}</span>
                </div>

                <Button
                  variant={plan.popular ? 'primary' : 'outline'}
                  size="lg"
                  className="w-full"
                  glow={plan.popular}
                  asChild
                >
                  <Link href={plan.name === 'Enterprise' ? '/contact' : '/register'}>
                    {plan.cta}
                  </Link>
                </Button>

                <ul className="space-y-3">
                  {plan.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-3">
                      <Check className="h-5 w-5 text-green-500 flex-shrink-0 mt-0.5" />
                      <span className="text-sm text-gray-700">{feature}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </Card>
          ))}
        </div>
      </div>
    </section>
  )
}
```

### 5.3 Dashboard Components

#### App Navbar

```tsx
// src/components/dashboard/app-navbar.tsx
'use client'

import Link from 'next/link'
import { Shield, Bell, Search, Settings, LogOut, User } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'

interface AppNavbarProps {
  user: {
    name: string
    email: string
    avatar?: string
  }
}

export function AppNavbar({ user }: AppNavbarProps) {
  return (
    <header className="sticky top-0 z-40 border-b border-gray-200 bg-white/80 backdrop-blur-xl">
      <nav className="container mx-auto px-4">
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <Link href="/dashboard" className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-primary-600 to-indigo-600">
              <Shield className="h-5 w-5 text-white" />
            </div>
            <span className="text-lg font-semibold text-gray-900">DevArchAI</span>
          </Link>

          {/* Search */}
          <div className="flex-1 max-w-md mx-8">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="search"
                placeholder="Search scans, reports, repositories..."
                className="w-full h-10 pl-10 pr-4 rounded-lg border border-gray-300 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
              />
            </div>
          </div>

          {/* Right side */}
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" className="relative">
              <Bell className="h-5 w-5" />
              <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-error-500" />
            </Button>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="gap-2">
                  <Avatar className="h-8 w-8">
                    <AvatarImage src={user.avatar} />
                    <AvatarFallback className="bg-primary-100 text-primary-700">
                      {user.name.charAt(0)}
                    </AvatarFallback>
                  </Avatar>
                  <span className="text-sm font-medium text-gray-700 hidden md:block">
                    {user.name}
                  </span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <div className="px-2 py-2">
                  <p className="text-sm font-medium text-gray-900">{user.name}</p>
                  <p className="text-xs text-gray-500">{user.email}</p>
                </div>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild>
                  <Link href="/settings" className="flex items-center gap-2">
                    <Settings className="h-4 w-4" />
                    Settings
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link href="/profile" className="flex items-center gap-2">
                    <User className="h-4 w-4" />
                    Profile
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild>
                  <Link href="/api/logout" className="flex items-center gap-2 text-error-600">
                    <LogOut className="h-4 w-4" />
                    Log out
                  </Link>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </nav>
    </header>
  )
}
```

#### Sidebar

```tsx
// src/components/dashboard/sidebar.tsx
'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard,
  ScanLine,
  FileText,
  FolderGit2,
  AlertTriangle,
  Settings,
  CreditCard,
  HelpCircle,
} from 'lucide-react'
import { cn } from '@/lib/utils'

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Scans', href: '/scans', icon: ScanLine },
  { name: 'Reports', href: '/reports', icon: FileText },
  { name: 'Repositories', href: '/repositories', icon: FolderGit2 },
  { name: 'Findings', href: '/findings', icon: AlertTriangle },
  { name: 'Settings', href: '/settings', icon: Settings },
  { name: 'Billing', href: '/billing', icon: CreditCard },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="w-64 border-r border-gray-200 bg-white">
      <div className="flex flex-col h-full">
        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1">
          {navigation.map((item) => {
            const Icon = item.icon
            const isActive = pathname === item.href

            return (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-gray-700 hover:bg-gray-100'
                )}
              >
                <Icon className={cn('h-5 w-5', isActive ? 'text-primary-600' : 'text-gray-500')} />
                {item.name}
              </Link>
            )
          })}
        </nav>

        {/* Help */}
        <div className="p-4 border-t border-gray-200">
          <Link
            href="/docs"
            className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-100 transition-colors"
          >
            <HelpCircle className="h-5 w-5 text-gray-500" />
            Documentation
          </Link>
        </div>
      </div>
    </aside>
  )
}
```

#### Score Gauge

```tsx
// src/components/dashboard/score-gauge.tsx
'use client'

import { motion } from 'framer-motion'

interface ScoreGaugeProps {
  score: number
  size?: 'sm' | 'md' | 'lg'
  showLabel?: boolean
}

export function ScoreGauge({ score, size = 'md', showLabel = true }: ScoreGaugeProps) {
  const radius = size === 'lg' ? 60 : size === 'md' ? 40 : 24
  const circumference = 2 * Math.PI * radius
  const progress = (score / 100) * circumference

  const getColor = (score: number) => {
    if (score >= 90) return 'text-success-500'
    if (score >= 80) return 'text-info-500'
    if (score >= 70) return 'text-warning-500'
    if (score >= 60) return 'text-orange-500'
    return 'text-error-500'
  }

  const getLabel = (score: number) => {
    if (score >= 90) return 'Excellent'
    if (score >= 80) return 'Good'
    if (score >= 70) return 'Fair'
    if (score >= 60) return 'Poor'
    return 'Critical'
  }

  const dimensions = {
    sm: { width: 64, height: 64, fontSize: 'text-lg' },
    md: { width: 96, height: 96, fontSize: 'text-2xl' },
    lg: { width: 144, height: 144, fontSize: 'text-4xl' },
  }

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg
        width={dimensions[size].width}
        height={dimensions[size].height}
        className="transform -rotate-90"
      >
        {/* Background circle */}
        <circle
          cx={dimensions[size].width / 2}
          cy={dimensions[size].height / 2}
          r={radius}
          className="text-gray-200"
          strokeWidth="8"
          stroke="currentColor"
          fill="transparent"
        />
        {/* Progress circle */}
        <motion.circle
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: circumference - progress }}
          transition={{ duration: 1, ease: 'easeOut' }}
          cx={dimensions[size].width / 2}
          cy={dimensions[size].height / 2}
          r={radius}
          className={getColor(score)}
          strokeWidth="8"
          stroke="currentColor"
          fill="transparent"
          strokeDasharray={circumference}
          strokeLinecap="round"
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className={cn('font-bold', dimensions[size].fontSize, getColor(score))}>
          {score}
        </span>
      </div>
      {showLabel && (
        <div className="absolute -bottom-6 left-1/2 -translate-x-1/2 whitespace-nowrap">
          <span className="text-xs font-medium text-gray-600">{getLabel(score)}</span>
        </div>
      )}
    </div>
  )
}
```

---

## 6. Page Specifications

### 6.1 Landing Page

**Route:** `/`  
**Layout:** Marketing layout (no sidebar)

#### Sections

1. **Navbar** - Logo, navigation, auth buttons
2. **Hero** - Headline, description, CTA, animation demo
3. **Stats** - Repos analyzed, rules, accuracy
4. **How It Works** - 5-step process
5. **Features Grid** - 4-6 feature cards
6. **Integrations** - Logo grid
7. **Testimonials** - Customer quotes
8. **Pricing** - 3-tier pricing cards
9. **CTA** - Final call-to-action
10. **Footer** - Links, legal, social

### 6.2 Login Page

**Route:** `/login`  
**Layout:** Auth layout (centered card)

#### Components

- Email/password form
- OAuth buttons (GitHub, Google, Microsoft)
- Forgot password link
- Signup link
- Security badges (SOC2, encryption)

### 6.3 Register Page

**Route:** `/register`  
**Layout:** Auth layout

#### Components

- Work email input
- Company name
- Password with strength indicator
- Terms acceptance
- OAuth signup
- Enterprise security indicators

### 6.4 Dashboard Page

**Route:** `/dashboard`  
**Layout:** App layout (navbar + sidebar)

#### Components

- Overview cards (total scans, avg score, findings)
- Recent scans list
- Score trend chart
- Category breakdown radar
- Quick scan input

### 6.5 Scans Page

**Route:** `/scans`  
**Layout:** App layout

#### Components

- Scan input (repo URL, branch selector)
- Scan list with filters
- Scan progress indicator
- Scan detail view

### 6.6 Report Page

**Route:** `/reports/:id`  
**Layout:** App layout

#### Components

- Report header (repo info, export buttons)
- Score overview (gauge + categories)
- Executive summary
- Findings list with filters
- Finding detail (expandable with AI explanation)
- Technology stack detected

### 6.7 Findings Page

**Route:** `/findings`  
**Layout:** App layout

#### Components

- Findings table (sortable, filterable)
- Severity filters
- Category filters
- Repository filters
- Bulk actions

### 6.8 Repositories Page

**Route:** `/repositories`  
**Layout:** App layout

#### Components

- Repository list/grid
- Add repository dialog
- Repository cards with latest scan info
- Delete repository action

### 6.9 Settings Page

**Route:** `/settings`  
**Layout:** App layout

#### Tabs

- Profile settings
- Notification preferences
- API keys
- Integrations
- Billing

### 6.10 Billing Page

**Route:** `/billing`  
**Layout:** App layout

#### Components

- Current plan card
- Usage metrics
- Plan upgrade options
- Payment methods
- Invoice history

---

## 7. API Integration

### 7.1 API Client

```typescript
// src/services/api.ts
import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'
import { useAuthStore } from '@/stores/auth-store'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
})

// Request interceptor - add auth token
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = useAuthStore.getState().accessToken
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor - handle token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        const refreshToken = useAuthStore.getState().refreshToken
        const response = await axios.post(`${API_BASE_URL}/api/v1/auth/refresh`, {
          refresh_token: refreshToken,
        })

        const { access_token } = response.data
        useAuthStore.getState().setTokens(access_token, refreshToken)

        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${access_token}`
        }

        return apiClient(originalRequest)
      } catch (refreshError) {
        useAuthStore.getState().logout()
        window.location.href = '/login'
        return Promise.reject(refreshError)
      }
    }

    return Promise.reject(error)
  }
)
```

### 7.2 React Query Hooks

```typescript
// src/hooks/use-scans.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { scansService } from '@/services/scans'
import type { ScanCreate, ScanResponse } from '@/types'

export function useScans(page = 1, pageSize = 20, statusFilter?: string) {
  return useQuery({
    queryKey: ['scans', page, pageSize, statusFilter],
    queryFn: () => scansService.list(page, pageSize, statusFilter),
    staleTime: 30000, // 30 seconds
  })
}

export function useScan(scanId: string) {
  return useQuery({
    queryKey: ['scan', scanId],
    queryFn: () => scansService.getById(scanId),
    enabled: !!scanId,
    refetchInterval: (query) => {
      const scan = query.state.data
      if (scan?.status === 'processing' || scan?.status === 'queued') {
        return 2000 // Poll every 2 seconds
      }
      return false
    },
  })
}

export function useCreateScan() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: ScanCreate) => scansService.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scans'] })
    },
  })
}

export function useCancelScan() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (scanId: string) => scansService.cancel(scanId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scans'] })
    },
  })
}
```

### 7.3 Services

```typescript
// src/services/scans.ts
import { apiClient } from './api'
import type { ScanCreate, ScanResponse, ScanProgressResponse } from '@/types'

export const scansService = {
  async list(page: number, pageSize: number, statusFilter?: string) {
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString(),
    })
    if (statusFilter) params.append('status_filter', statusFilter)

    const response = await apiClient.get<ScanResponse[]>(`/api/v1/scans?${params}`)
    return response.data
  },

  async getById(scanId: string) {
    const response = await apiClient.get<ScanResponse>(`/api/v1/scans/${scanId}`)
    return response.data
  },

  async create(data: ScanCreate) {
    const response = await apiClient.post<ScanResponse>('/api/v1/scans', data)
    return response.data
  },

  async cancel(scanId: string) {
    const response = await apiClient.post(`/api/v1/scans/${scanId}/cancel`)
    return response.data
  },

  async getProgress(scanId: string) {
    const response = await apiClient.get<ScanProgressResponse>(`/api/v1/scans/${scanId}/progress`)
    return response.data
  },
}
```

---

## 8. Implementation Roadmap

### Phase 1: Foundation (Week 1-2)

- [ ] Set up Next.js 14 project with TypeScript
- [ ] Configure Tailwind CSS with design system
- [ ] Implement base UI components (Button, Card, Input, etc.)
- [ ] Set up authentication flow
- [ ] Create marketing layout and navbar
- [ ] Build landing page

### Phase 2: Authentication (Week 3)

- [ ] Login page with email/password
- [ ] Register page with validation
- [ ] OAuth integration (GitHub, Google)
- [ ] Password reset flow
- [ ] Auth state management

### Phase 3: Dashboard (Week 4-5)

- [ ] App layout with sidebar
- [ ] Dashboard overview page
- [ ] Scan creation flow
- [ ] Scan list and progress tracking
- [ ] Report viewing page

### Phase 4: Reports & Findings (Week 6-7)

- [ ] Report visualization components
- [ ] Findings list with filters
- [ ] Finding detail view
- [ ] Export functionality (JSON, PDF, Excel)
- [ ] Category charts and graphs

### Phase 5: Polish & Testing (Week 8)

- [ ] Dark mode implementation
- [ ] Mobile responsiveness
- [ ] Performance optimization
- [ ] Unit tests for components
- [ ] E2E tests for critical flows
- [ ] Accessibility audit

### Phase 6: Production Ready (Week 9-10)

- [ ] Analytics integration
- [ ] Error tracking (Sentry)
- [ ] SEO optimization
- [ ] Documentation
- [ ] Performance monitoring
- [ ] Security review

---

## 9. UX Improvements for DevOps Engineers

### 9.1 Keyboard Shortcuts

```typescript
// Global shortcuts
Cmd+K - Command palette (search)
Cmd+Enter - Submit current form
Esc - Close modals/dropdowns
? - Show keyboard shortcuts

// Navigation
G then D - Go to Dashboard
G then S - Go to Scans
G then R - Go to Reports
G then F - Go to Findings
```

### 9.2 Command Palette

```tsx
// src/components/command-palette.tsx
'use client'

import { useState } from 'react'
import { Command } from 'cmdk'
import { Search, FileText, ScanLine, Settings } from 'lucide-react'

export function CommandPalette() {
  const [open, setOpen] = useState(false)

  // Toggle with Cmd+K
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        setOpen((open) => !open)
      }
    }
    document.addEventListener('keydown', down)
    return () => document.removeEventListener('keydown', down)
  }, [])

  return (
    <Command.Dialog open={open} onOpenChange={setOpen} label="Command Palette">
      <div className="flex items-center gap-2 border-b px-3">
        <Search className="h-5 w-5 text-gray-400" />
        <Command.Input
          placeholder="Type a command or search..."
          className="flex-1 h-12 outline-none"
        />
      </div>
      <Command.List>
        <Command.Empty>No results found.</Command.Empty>
        <Command.Group heading="Suggestions">
          <Command.Item>
            <ScanLine className="h-4 w-4" />
            <span>New Scan</span>
          </Command.Item>
          <Command.Item>
            <FileText className="h-4 w-4" />
            <span>View Reports</span>
          </Command.Item>
          <Command.Item>
            <Settings className="h-4 w-4" />
            <span>Settings</span>
          </Command.Item>
        </Command.Group>
      </Command.List>
    </Command.Dialog>
  )
}
```

### 9.3 Real-time Updates

```typescript
// src/hooks/use-scan-realtime.ts
import { useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'

export function useScanRealtime(scanId: string) {
  const queryClient = useQueryClient()

  useEffect(() => {
    // WebSocket connection for real-time updates
    const ws = new WebSocket(process.env.NEXT_PUBLIC_WS_URL!)

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'scan_update' && data.scan_id === scanId) {
        queryClient.setQueryData(['scan', scanId], data.scan)
      }
    }

    return () => ws.close()
  }, [scanId, queryClient])
}
```

### 9.4 Bulk Actions

```tsx
// src/components/findings/findings-bulk-actions.tsx
'use client'

import { Download, CheckSquare, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

interface BulkActionsProps {
  selectedCount: number
  onExport: (format: string) => void
  onClearSelection: () => void
}

export function FindingsBulkActions({ selectedCount, onExport, onClearSelection }: BulkActionsProps) {
  if (selectedCount === 0) return null

  return (
    <div className="sticky top-16 z-30 flex items-center justify-between p-4 bg-primary-50 border-b border-primary-200">
      <div className="flex items-center gap-3">
        <CheckSquare className="h-5 w-5 text-primary-600" />
        <span className="text-sm font-medium text-primary-700">
          {selectedCount} findings selected
        </span>
      </div>
      <div className="flex items-center gap-2">
        <Button variant="outline" size="sm" onClick={() => onExport('json')}>
          Export JSON
        </Button>
        <Button variant="outline" size="sm" onClick={() => onExport('csv')}>
          Export CSV
        </Button>
        <Button variant="ghost" size="sm" onClick={onClearSelection}>
          <X className="h-4 w-4 mr-2" />
          Clear
        </Button>
      </div>
    </div>
  )
}
```

---

## 10. Integration Points with Backend APIs

### 10.1 Authentication Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Backend   │────▶│   GitHub    │
│             │     │   API       │     │   OAuth     │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       │  1. Login         │                   │
       │──────────────────▶│                   │
       │                   │                   │
       │  2. OAuth URL     │                   │
       │◀──────────────────│                   │
       │                   │                   │
       │  3. Redirect      │                   │
       │──────────────────────────────────────▶│
       │                   │                   │
       │  4. Callback      │                   │
       │◀──────────────────────────────────────│
       │                   │                   │
       │  5. Exchange code │                   │
       │──────────────────────────────────────▶│
       │                   │                   │
       │  6. User info     │                   │
       │◀──────────────────────────────────────│
       │                   │                   │
       │  7. JWT tokens    │                   │
       │◀──────────────────│                   │
       │                   │                   │
```

### 10.2 Scan Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Backend   │────▶│   Celery    │
│             │     │   API       │     │   Workers   │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       │  1. Create scan   │                   │
       │──────────────────▶│                   │
       │                   │                   │
       │  2. Scan created  │                   │
       │◀──────────────────│                   │
       │                   │  3. Queue task    │
       │                   │──────────────────▶│
       │                   │                   │
       │  4. Poll status   │                   │
       │──────────────────▶│                   │
       │                   │                   │
       │  5. Processing    │                   │
       │◀──────────────────│                   │
       │                   │                   │
       │  6. Completed     │                   │
       │◀──────────────────│                   │
       │                   │                   │
```

### 10.3 Report Export Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Backend   │────▶│   S3/GCS    │
│             │     │   API       │     │   Storage   │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       │  1. Export PDF    │                   │
       │──────────────────▶│                   │
       │                   │                   │
       │  2. Generate      │                   │
       │                   │──────────────────▶│
       │                   │                   │
       │  3. Download URL  │                   │
       │◀──────────────────│                   │
       │                   │                   │
       │  4. Download      │                   │
       │──────────────────────────────────────▶│
       │                   │                   │
```

---

## 11. Performance Optimization

### 11.1 Code Splitting

```typescript
// Lazy load heavy components
const ReportChart = lazy(() => import('@/components/reports/report-chart'))
const FindingsTable = lazy(() => import('@/components/findings/findings-table'))

// Route-based code splitting (Next.js automatic)
// Each route in app/ is automatically code-split
```

### 11.2 Image Optimization

```typescript
// Use Next.js Image component
import Image from 'next/image'

<Image
  src="/images/logos/github.svg"
  alt="GitHub"
  width={128}
  height={32}
  priority
  className="h-8 w-auto"
/>
```

### 11.3 React Query Optimization

```typescript
// Configure optimal caching
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      gcTime: 10 * 60 * 1000, // 10 minutes
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
})
```

---

## 12. Security Considerations

### 12.1 Frontend Security

1. **XSS Prevention**
   - Use React's built-in escaping
   - Sanitize user-generated content with DOMPurify
   - Avoid `dangerouslySetInnerHTML`

2. **CSRF Protection**
   - Use SameSite cookies
   - Include CSRF tokens in forms

3. **Authentication**
   - Store tokens in httpOnly cookies (preferred) or memory
   - Implement token refresh
   - Auto-logout on inactivity

4. **Content Security Policy**
   ```html
   <meta
     http-equiv="Content-Security-Policy"
     content="default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';"
   />
   ```

### 12.2 Enterprise Security Indicators

Display on login/register pages:
- SOC2 Type II certified
- GDPR compliant
- End-to-end encryption
- Data residency options
- SSO/SAML support

---

## 13. Conclusion

This frontend architecture provides a production-ready foundation for DevArchAI, matching the quality and user experience of leading DevOps SaaS platforms. The design system, component library, and implementation roadmap ensure consistent, scalable development that meets enterprise standards.

Key differentiators:
- **Modern Stack**: Next.js 14, TypeScript, Tailwind CSS
- **Enterprise UX**: Professional design, accessibility, performance
- **DevOps Focused**: Keyboard shortcuts, real-time updates, bulk actions
- **Scalable**: Component-driven, well-tested, documented

The architecture supports rapid iteration while maintaining code quality and user experience standards expected by enterprise DevOps teams.
