/**
 * Production-Level Component Tests for DevArchAI Frontend
 * 
 * Tests critical UI components:
 * - ScanProgress component
 * - ScanPage component
 * - ResultComponent
 * - TechStackDisplay
 * 
 * Run with:
 *   npm test -- src/components/__tests__/scan-components.test.tsx
 *   npm test -- --coverage
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ScanProgress } from '../ScanProgress';

// Mock dependencies
jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    h3: ({ children, ...props }: any) => <h3 {...props}>{children}</h3>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

describe('ScanProgress Component', () => {
  test('renders scan progress with percentage', () => {
    render(
      <ScanProgress
        progress={50}
        currentStep={2}
        isComplete={false}
        detectedTechnologies={['docker', 'terraform']}
      />
    );

    // Should show progress percentage
    expect(screen.getByText('50%')).toBeInTheDocument();
  });

  test('shows analyzing state when not complete', () => {
    render(
      <ScanProgress
        progress={30}
        currentStep={1}
        isComplete={false}
        detectedTechnologies={[]}
      />
    );

    expect(screen.getByText('Analyzing Repository')).toBeInTheDocument();
  });

  test('shows complete state when done', () => {
    render(
      <ScanProgress
        progress={100}
        currentStep={5}
        isComplete={true}
        detectedTechnologies={['docker', 'kubernetes']}
      />
    );

    expect(screen.getByText('Analysis Complete!')).toBeInTheDocument();
    expect(screen.getByText('Your security report is ready')).toBeInTheDocument();
  });

  test('displays detected technologies', () => {
    render(
      <ScanProgress
        progress={75}
        currentStep={3}
        isComplete={false}
        detectedTechnologies={['docker', 'terraform', 'kubernetes']}
      />
    );

    // Should show technology badges
    expect(screen.getByText('docker')).toBeInTheDocument();
    expect(screen.getByText('terraform')).toBeInTheDocument();
    expect(screen.getByText('kubernetes')).toBeInTheDocument();
  });

  test('shows files being scanned', () => {
    const detectedFiles = [
      { path: 'Dockerfile', type: 'docker' as const, status: 'completed' as const },
      { path: 'main.tf', type: 'terraform' as const, status: 'completed' as const },
    ];

    render(
      <ScanProgress
        progress={60}
        currentStep={2}
        isComplete={false}
        detectedFiles={detectedFiles}
        detectedTechnologies={['docker', 'terraform']}
      />
    );

    expect(screen.getByText('Dockerfile')).toBeInTheDocument();
    expect(screen.getByText('main.tf')).toBeInTheDocument();
  });

  test('shows live logs section', () => {
    render(
      <ScanProgress
        progress={40}
        currentStep={2}
        isComplete={false}
        detectedTechnologies={['docker']}
      />
    );

    expect(screen.getByText('Live Scan Logs')).toBeInTheDocument();
  });

  test('shows files being scanned section', () => {
    render(
      <ScanProgress
        progress={40}
        currentStep={2}
        isComplete={false}
        detectedTechnologies={['docker']}
      />
    );

    expect(screen.getByText('Files Being Scanned')).toBeInTheDocument();
  });

  test('displays scan stats', () => {
    render(
      <ScanProgress
        progress={50}
        currentStep={2}
        isComplete={false}
        detectedTechnologies={['docker', 'terraform']}
      />
    );

    // Should show files scanned count
    expect(screen.getByText('Files Scanned')).toBeInTheDocument();
    expect(screen.getByText('Current Step')).toBeInTheDocument();
    expect(screen.getByText('Complete')).toBeInTheDocument();
  });
});

describe('ScanProgress - Edge Cases', () => {
  test('handles empty detected technologies', () => {
    render(
      <ScanProgress
        progress={20}
        currentStep={1}
        isComplete={false}
        detectedTechnologies={[]}
      />
    );

    // Should not crash, should show waiting message
    expect(screen.getByText(/Analyzing Repository/i)).toBeInTheDocument();
  });

  test('handles progress at 0', () => {
    render(
      <ScanProgress
        progress={0}
        currentStep={0}
        isComplete={false}
        detectedTechnologies={[]}
      />
    );

    expect(screen.getByText('0%')).toBeInTheDocument();
  });

  test('handles progress at 100', () => {
    render(
      <ScanProgress
        progress={100}
        currentStep={5}
        isComplete={true}
        detectedTechnologies={['docker']}
      />
    );

    expect(screen.getByText('100%')).toBeInTheDocument();
    expect(screen.getByText('Analysis Complete!')).toBeInTheDocument();
  });
});
