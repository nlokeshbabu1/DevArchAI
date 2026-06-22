import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ScanProgress } from '../ScanProgress';

vi.mock('framer-motion', () => ({
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
    expect(screen.getByText('Analysis Complete')).toBeInTheDocument();
    expect(screen.getByText('Your security report is ready')).toBeInTheDocument();
  });

  test('shows stat labels', () => {
    render(
      <ScanProgress
        progress={75}
        currentStep={3}
        isComplete={false}
        detectedTechnologies={['docker', 'terraform', 'kubernetes']}
      />
    );
    expect(screen.getByText('Current Stage')).toBeInTheDocument();
    expect(screen.getByText('Files Scanned')).toBeInTheDocument();
    expect(screen.getByText('Technologies')).toBeInTheDocument();
    expect(screen.getByText('Findings')).toBeInTheDocument();
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
    expect(screen.getByText('Live Logs')).toBeInTheDocument();
  });

  test('shows active stage name in header', () => {
    render(
      <ScanProgress
        progress={60}
        currentStep={2}
        isComplete={false}
        detectedTechnologies={['docker', 'terraform']}
      />
    );
    expect(screen.getAllByText('Cloning Repository').length).toBe(3);
  });

  test('displays technology count in stats', () => {
    render(
      <ScanProgress
        progress={75}
        currentStep={3}
        isComplete={false}
        detectedTechnologies={['docker', 'terraform', 'kubernetes']}
      />
    );
    expect(screen.getByText('3')).toBeInTheDocument();
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

  test('handles progress at 100 with completion', () => {
    render(
      <ScanProgress
        progress={100}
        currentStep={5}
        isComplete={true}
        detectedTechnologies={['docker']}
      />
    );
    expect(screen.getByText('100%')).toBeInTheDocument();
    expect(screen.getByText('Analysis Complete')).toBeInTheDocument();
  });

  test('shows Complete stat value when done', () => {
    render(
      <ScanProgress
        progress={100}
        currentStep={7}
        isComplete={true}
        detectedTechnologies={[]}
        filesScanned={42}
        findingsDetected={5}
      />
    );
    expect(screen.getByText('Complete')).toBeInTheDocument();
    expect(screen.getByText('42')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
  });
});
