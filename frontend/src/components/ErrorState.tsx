import React from 'react';
import { StyleSheet, Text, View, TouchableOpacity, SafeAreaView } from 'react-native';
import { THEME } from '../constants/theme';

interface ErrorStateProps {
  targetUrl: string;
  errorMessage?: string;
  onRetry: () => void;
  onBack: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  targetUrl,
  errorMessage = "Something went wrong while analysing the website. Please ensure the domain name is typed correctly and that the website is online.",
  onRetry,
  onBack,
}) => {
  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.container}>
        {/* Error Icon Header */}
        <View style={styles.iconCircle}>
          <Text style={styles.errorIcon}>✕</Text>
        </View>

        <Text style={styles.title}>We couldn't analyse this website</Text>
        <Text style={styles.domainText}>{targetUrl}</Text>

        {/* Error Card */}
        <View style={styles.card}>
          <Text style={styles.cardHeader}>WHAT HAPPENED</Text>
          <Text style={styles.explanationText}>{errorMessage}</Text>

          <View style={styles.suggestionsBox}>
            <Text style={styles.suggestionsTitle}>Things to check:</Text>
            <Text style={styles.suggestionItem}>• Double check for typos in the address</Text>
            <Text style={styles.suggestionItem}>• Ensure the website is reachable in your browser</Text>
            <Text style={styles.suggestionItem}>• Verify your internet connection</Text>
          </View>
        </View>

        {/* Actions */}
        <TouchableOpacity style={styles.primaryButton} onPress={onRetry} activeOpacity={0.85}>
          <Text style={styles.primaryButtonText}>Try Again</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.secondaryButton} onPress={onBack} activeOpacity={0.7}>
          <Text style={styles.secondaryButtonText}>← Back to Home</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: THEME.colors.background,
  },
  container: {
    flex: 1,
    justifyContent: 'center',
    padding: THEME.spacing.lg,
  },
  iconCircle: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: THEME.colors.failBg,
    borderWidth: 1,
    borderColor: THEME.colors.failBorder,
    alignItems: 'center',
    justifyContent: 'center',
    alignSelf: 'center',
    marginBottom: THEME.spacing.md,
  },
  errorIcon: {
    fontSize: 28,
    color: THEME.colors.fail,
    fontWeight: '900',
  },
  title: {
    fontSize: 22,
    fontWeight: '800',
    color: THEME.colors.textPrimary,
    textAlign: 'center',
    marginBottom: 4,
  },
  domainText: {
    fontSize: 13,
    color: THEME.colors.primaryLight,
    textAlign: 'center',
    marginBottom: THEME.spacing.lg,
  },
  card: {
    backgroundColor: THEME.colors.surface,
    borderRadius: THEME.borderRadius.lg,
    padding: THEME.spacing.lg,
    borderWidth: 1,
    borderColor: THEME.colors.border,
    marginBottom: THEME.spacing.lg,
  },
  cardHeader: {
    fontSize: 11,
    fontWeight: '800',
    color: THEME.colors.textMuted,
    letterSpacing: 0.8,
    marginBottom: 8,
  },
  explanationText: {
    fontSize: 14,
    color: THEME.colors.textSecondary,
    lineHeight: 20,
    marginBottom: THEME.spacing.md,
  },
  suggestionsBox: {
    backgroundColor: 'rgba(15, 23, 42, 0.5)',
    borderRadius: THEME.borderRadius.sm,
    padding: 12,
    borderWidth: 1,
    borderColor: THEME.colors.border,
  },
  suggestionsTitle: {
    fontSize: 12,
    fontWeight: '700',
    color: THEME.colors.textPrimary,
    marginBottom: 6,
  },
  suggestionItem: {
    fontSize: 12,
    color: THEME.colors.textSecondary,
    lineHeight: 18,
    marginBottom: 2,
  },
  primaryButton: {
    backgroundColor: THEME.colors.primary,
    borderRadius: THEME.borderRadius.md,
    paddingVertical: 15,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 10,
  },
  primaryButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '700',
  },
  secondaryButton: {
    backgroundColor: THEME.colors.surfaceLight,
    borderRadius: THEME.borderRadius.md,
    paddingVertical: 13,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: THEME.colors.border,
  },
  secondaryButtonText: {
    color: THEME.colors.textSecondary,
    fontSize: 14,
    fontWeight: '600',
  },
});
