import React, { useEffect, useState } from 'react';
import { StyleSheet, Text, View, ActivityIndicator } from 'react-native';
import { THEME } from '../constants/theme';

interface Step {
  id: number;
  label: string;
}

const STEPS: Step[] = [
  { id: 1, label: 'Preparing website analysis' },
  { id: 2, label: 'Checking technical SEO' },
  { id: 3, label: 'Reviewing website content' },
  { id: 4, label: 'Understanding your audience' },
  { id: 5, label: 'Comparing local visibility' },
  { id: 6, label: 'Building recommendations' },
];

interface LoadingStateProps {
  targetUrl: string;
  onComplete: () => void;
  shouldSimulateError?: boolean;
  onError: () => void;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  targetUrl,
  onComplete,
  shouldSimulateError = false,
  onError,
}) => {
  const [currentStep, setCurrentStep] = useState<number>(1);

  useEffect(() => {
    // Step-by-step progress timer (500ms per step = 3 seconds total simulation)
    const interval = setInterval(() => {
      setCurrentStep((prev) => {
        if (shouldSimulateError && prev === 3) {
          clearInterval(interval);
          onError();
          return prev;
        }

        if (prev >= STEPS.length) {
          clearInterval(interval);
          setTimeout(() => {
            onComplete();
          }, 400);
          return prev;
        }
        return prev + 1;
      });
    }, 550);

    return () => clearInterval(interval);
  }, [shouldSimulateError]);

  const progressPercentage = Math.min(100, Math.round((currentStep / STEPS.length) * 100));

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <ActivityIndicator size="large" color={THEME.colors.primaryLight} style={styles.spinner} />
        <Text style={styles.title}>Analysing your website</Text>
        <Text style={styles.subtitle}>This may take a moment...</Text>
        <Text style={styles.targetDomain} numberOfLines={1}>
          {targetUrl}
        </Text>
      </View>

      {/* Progress Card */}
      <View style={styles.card}>
        {/* Progress Bar Header */}
        <View style={styles.progressHeader}>
          <Text style={styles.progressStepCount}>
            Step {currentStep} of {STEPS.length}
          </Text>
          <Text style={styles.progressPercentage}>{progressPercentage}%</Text>
        </View>

        {/* Progress Bar Track */}
        <View style={styles.progressBarTrack}>
          <View style={[styles.progressBarFill, { width: `${progressPercentage}%` }]} />
        </View>

        {/* Step Items Checklist */}
        <View style={styles.stepsList}>
          {STEPS.map((step) => {
            const isCompleted = step.id < currentStep;
            const isActive = step.id === currentStep;
            const isPending = step.id > currentStep;

            return (
              <View key={step.id} style={styles.stepRow}>
                {isCompleted && (
                  <View style={[styles.iconContainer, styles.iconCompleted]}>
                    <Text style={styles.checkIcon}>✓</Text>
                  </View>
                )}

                {isActive && (
                  <View style={[styles.iconContainer, styles.iconActive]}>
                    <Text style={styles.activeDot}>●</Text>
                  </View>
                )}

                {isPending && (
                  <View style={[styles.iconContainer, styles.iconPending]}>
                    <Text style={styles.pendingDot}>○</Text>
                  </View>
                )}

                <Text
                  style={[
                    styles.stepLabel,
                    isCompleted && styles.labelCompleted,
                    isActive && styles.labelActive,
                    isPending && styles.labelPending,
                  ]}
                >
                  {step.label}
                  {isActive ? ' ...' : ''}
                </Text>
              </View>
            );
          })}
        </View>
      </View>

      <Text style={styles.footerNote}>
        Auditing mobile readiness, structured data, content depth and local ranking factors.
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    padding: THEME.spacing.lg,
  },
  header: {
    alignItems: 'center',
    marginBottom: THEME.spacing.xl,
  },
  spinner: {
    marginBottom: THEME.spacing.md,
  },
  title: {
    fontSize: 24,
    fontWeight: '800',
    color: THEME.colors.textPrimary,
    textAlign: 'center',
  },
  subtitle: {
    fontSize: 14,
    color: THEME.colors.textSecondary,
    marginTop: 4,
    textAlign: 'center',
  },
  targetDomain: {
    fontSize: 13,
    color: THEME.colors.primaryLight,
    marginTop: 8,
    backgroundColor: THEME.colors.surfaceLight,
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: THEME.borderRadius.full,
    maxWidth: '85%',
  },
  card: {
    backgroundColor: THEME.colors.surface,
    borderRadius: THEME.borderRadius.lg,
    padding: THEME.spacing.lg,
    borderWidth: 1,
    borderColor: THEME.colors.border,
  },
  progressHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  progressStepCount: {
    fontSize: 12,
    fontWeight: '700',
    color: THEME.colors.textSecondary,
    letterSpacing: 0.5,
  },
  progressPercentage: {
    fontSize: 12,
    fontWeight: '800',
    color: THEME.colors.primaryLight,
  },
  progressBarTrack: {
    height: 6,
    backgroundColor: THEME.colors.background,
    borderRadius: 3,
    overflow: 'hidden',
    marginBottom: THEME.spacing.lg,
  },
  progressBarFill: {
    height: '100%',
    backgroundColor: THEME.colors.primary,
    borderRadius: 3,
  },
  stepsList: {
    gap: 12,
  },
  stepRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  iconContainer: {
    width: 22,
    height: 22,
    borderRadius: 11,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  iconCompleted: {
    backgroundColor: THEME.colors.passBg,
    borderWidth: 1,
    borderColor: THEME.colors.passBorder,
  },
  iconActive: {
    backgroundColor: THEME.colors.primary,
  },
  iconPending: {
    backgroundColor: THEME.colors.background,
    borderWidth: 1,
    borderColor: THEME.colors.border,
  },
  checkIcon: {
    fontSize: 12,
    fontWeight: '900',
    color: THEME.colors.pass,
  },
  activeDot: {
    fontSize: 10,
    color: '#FFFFFF',
  },
  pendingDot: {
    fontSize: 10,
    color: THEME.colors.textMuted,
  },
  stepLabel: {
    fontSize: 14,
    lineHeight: 18,
  },
  labelCompleted: {
    color: THEME.colors.textPrimary,
    fontWeight: '500',
  },
  labelActive: {
    color: THEME.colors.primaryLight,
    fontWeight: '700',
  },
  labelPending: {
    color: THEME.colors.textMuted,
  },
  footerNote: {
    fontSize: 12,
    color: THEME.colors.textMuted,
    textAlign: 'center',
    marginTop: THEME.spacing.lg,
    lineHeight: 16,
  },
});
